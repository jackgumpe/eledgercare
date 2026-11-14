using System.Net;
using System.Net.Sockets;
using System.Text;

namespace ELedgerCare.Acceptance.Tests.Harness;

/// <summary>Raw HTTP/1.1 over a loopback socket, for boundaries HttpClient cannot express.</summary>
public static class RawHttp
{
    /// <summary>
    /// Sends request headers declaring <paramref name="declaredLength"/> bytes, writes only
    /// <paramref name="bodyPrefix"/>, then abortively closes the connection (RST) without finishing.
    /// </summary>
    public static async Task SendPartialBodyAndDisconnectAsync(Uri baseAddress, Guid key, int declaredLength, byte[] bodyPrefix)
    {
        using var client = new TcpClient();
        await client.ConnectAsync(IPAddress.Loopback, baseAddress.Port);
        var stream = client.GetStream();
        var headers = $"POST /api/documents HTTP/1.1\r\nHost: 127.0.0.1:{baseAddress.Port}\r\n" +
                      $"Content-Type: application/pdf\r\nIdempotency-Key: {key:D}\r\nContent-Length: {declaredLength}\r\n\r\n";
        await stream.WriteAsync(Encoding.ASCII.GetBytes(headers));
        await stream.WriteAsync(bodyPrefix);
        await stream.FlushAsync();
        await Task.Delay(300);
        client.Client.LingerState = new LingerOption(true, 0);
        client.Close();
    }

    /// <summary>Sends headers only (declaring a length) and returns the status line the server answers with.</summary>
    public static async Task<string> SendHeadersOnlyAsync(Uri baseAddress, Guid key, long declaredLength)
    {
        using var client = new TcpClient();
        await client.ConnectAsync(IPAddress.Loopback, baseAddress.Port);
        var stream = client.GetStream();
        var headers = $"POST /api/documents HTTP/1.1\r\nHost: 127.0.0.1:{baseAddress.Port}\r\n" +
                      $"Content-Type: application/pdf\r\nIdempotency-Key: {key:D}\r\nContent-Length: {declaredLength}\r\n\r\n";
        await stream.WriteAsync(Encoding.ASCII.GetBytes(headers));
        await stream.FlushAsync();
        var buffer = new byte[1024];
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var read = await stream.ReadAsync(buffer, timeout.Token);
        var text = Encoding.ASCII.GetString(buffer, 0, read);
        return text.Split("\r\n")[0];
    }
}

/// <summary>
/// A controlled local proxy that forwards one request to the API, waits until the API has started
/// sending its response (i.e. after the server committed and replied), then closes the client
/// connection without relaying any response bytes: a committed-but-unobserved receipt.
/// </summary>
public sealed class ResponseDroppingProxy : IAsyncDisposable
{
    private readonly TcpListener listener = new(IPAddress.Loopback, 0);
    private readonly Uri upstream;
    private readonly Task<string> session;

    public ResponseDroppingProxy(Uri upstream)
    {
        this.upstream = upstream;
        listener.Start();
        session = RunAsync();
    }

    public Uri Address => new($"http://127.0.0.1:{((IPEndPoint)listener.LocalEndpoint).Port}");

    /// <summary>The status line of the dropped upstream response.</summary>
    public Task<string> DroppedStatusLine => session;

    public ValueTask DisposeAsync()
    {
        listener.Stop();
        listener.Dispose();
        return ValueTask.CompletedTask;
    }

    private async Task<string> RunAsync()
    {
        using var client = await listener.AcceptTcpClientAsync();
        using var server = new TcpClient();
        await server.ConnectAsync(IPAddress.Loopback, upstream.Port);
        var clientStream = client.GetStream();
        var serverStream = server.GetStream();

        using var forwarding = new CancellationTokenSource();
        var pump = clientStream.CopyToAsync(serverStream, forwarding.Token);

        var buffer = new byte[4096];
        var read = await serverStream.ReadAsync(buffer).AsTask().WaitAsync(TimeSpan.FromSeconds(60));
        var statusLine = Encoding.ASCII.GetString(buffer, 0, read).Split("\r\n")[0];

        await forwarding.CancelAsync();
        client.Client.LingerState = new LingerOption(true, 0);
        client.Close();
        server.Close();
        try
        {
            await pump;
        }
        catch (Exception ex) when (ex is OperationCanceledException or IOException or ObjectDisposedException)
        {
            // Expected: the pump stops when both sockets close.
        }

        return statusLine;
    }
}
