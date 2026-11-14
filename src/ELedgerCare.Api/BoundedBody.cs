namespace ELedgerCare.Api;

/// <summary>
/// Reads a request body into memory without exceeding a byte limit, independent of any declared
/// Content-Length. No temporary files or upload directories are used.
/// </summary>
internal static class BoundedBody
{
    private const int ChunkSize = 81_920;

    public static async Task<byte[]> ReadAsync(Stream body, int maxBytes, CancellationToken cancellationToken)
    {
        using var buffer = new MemoryStream();
        var chunk = new byte[ChunkSize];
        while (true)
        {
            var read = await body.ReadAsync(chunk, cancellationToken);
            if (read == 0)
            {
                return buffer.ToArray();
            }

            if (buffer.Length + read > maxBytes)
            {
                throw new LimitExceededException();
            }

            buffer.Write(chunk, 0, read);
        }
    }

    public sealed class LimitExceededException : Exception
    {
        public LimitExceededException()
            : base("Request body exceeded the configured limit.")
        {
        }

        public LimitExceededException(string message)
            : base(message)
        {
        }

        public LimitExceededException(string message, Exception innerException)
            : base(message, innerException)
        {
        }
    }
}
