using System.Threading.Channels;
using ELedgerCare.Application.Extraction;

namespace ELedgerCare.Api;

public interface IExtractionWakeSignal
{
    void NotifyWorkQueued();
}

/// <summary>
/// Single-concurrency local OCR background supervisor. Reconciles abandoned running attempts on startup
/// (even when execution is disabled) after verifying old processes are gone, and claims queued jobs
/// sequentially only when LocalOcr:Enabled is true.
/// </summary>
internal sealed partial class ExtractionSupervisorService(
    ExtractionAttemptCoordinator coordinator,
    ExtractionSettings settings,
    ILogger<ExtractionSupervisorService> logger) : BackgroundService, IExtractionWakeSignal
{
    private readonly Channel<bool> wakeChannel = Channel.CreateBounded<bool>(new BoundedChannelOptions(1)
    {
        FullMode = BoundedChannelFullMode.DropWrite,
        SingleReader = true,
        SingleWriter = false,
    });

    public void NotifyWorkQueued() => wakeChannel.Writer.TryWrite(true);

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        try
        {
            var recoveredAtStartup = await coordinator.ReconcileAbandonedAttemptsAsync(stoppingToken);
            if (recoveredAtStartup > 0)
            {
                LogRecoveredAttempts(logger, recoveredAtStartup);
            }
        }
        catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
        {
            return;
        }
        catch (Exception ex)
        {
            LogSupervisorLoopError(logger, ex);
        }

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await coordinator.ReconcileAbandonedAttemptsAsync(stoppingToken);

                if (settings.Enabled)
                {
                    while (!stoppingToken.IsCancellationRequested &&
                           await coordinator.ExecuteNextQueuedAttemptAsync(stoppingToken))
                    {
                        // Drain remaining queued jobs sequentially at concurrency 1.
                    }
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                LogSupervisorLoopError(logger, ex);
            }

            using var delayCts = CancellationTokenSource.CreateLinkedTokenSource(stoppingToken);
            delayCts.CancelAfter(TimeSpan.FromSeconds(2));
            try
            {
                await wakeChannel.Reader.WaitToReadAsync(delayCts.Token);
                while (wakeChannel.Reader.TryRead(out _))
                {
                }
            }
            catch (OperationCanceledException) when (!stoppingToken.IsCancellationRequested)
            {
                // Periodic poll window elapsed.
            }
            catch (OperationCanceledException)
            {
                break;
            }
        }
    }

    [LoggerMessage(Level = LogLevel.Information, Message = "Reconciled {Count} abandoned extraction attempt(s) to interrupted state.")]
    private static partial void LogRecoveredAttempts(ILogger logger, int count);

    [LoggerMessage(Level = LogLevel.Error, Message = "Unexpected error in ExtractionSupervisorService loop.")]
    private static partial void LogSupervisorLoopError(ILogger logger, Exception exception);
}
