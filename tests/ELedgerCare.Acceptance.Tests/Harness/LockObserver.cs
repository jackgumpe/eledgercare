using Npgsql;

namespace ELedgerCare.Acceptance.Tests.Harness;

public sealed record LockRow(string LockType, string Relation, string Mode, bool Granted);

public sealed record BlockedBackend(
    int Pid,
    string? State,
    string? WaitEventType,
    string? WaitEvent,
    string? BackendXid,
    string Query,
    IReadOnlyList<LockRow> Locks);

/// <summary>
/// Observes the API's own database backends (by database and runtime role) while a harness connection
/// holds a table lock. Reads only pg_stat_activity/pg_locks rows for the owned test database.
/// </summary>
public static class LockObserver
{
    public static async Task<IReadOnlyList<BlockedBackend>> WaitForBlockedAsync(
        TestDatabase database, string appUser, int expected, TimeSpan timeout)
    {
        await using var admin = await database.OpenAdminAsync();
        var deadline = DateTime.UtcNow + timeout;
        while (true)
        {
            var blocked = await ReadAsync(admin, database.Name, appUser);
            if (blocked.Count >= expected)
            {
                return blocked;
            }

            if (DateTime.UtcNow > deadline)
            {
                throw new TimeoutException($"Expected {expected} lock-blocked API backends, observed {blocked.Count}.");
            }

            await Task.Delay(50);
        }
    }

    public static async Task<bool> BackendGoneAsync(TestDatabase database, int pid, TimeSpan timeout)
    {
        await using var admin = await database.OpenAdminAsync();
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
        {
            await using var command = new NpgsqlCommand("SELECT count(*) FROM pg_stat_activity WHERE pid = @pid", admin);
            command.Parameters.AddWithValue("pid", pid);
            if ((long)(await command.ExecuteScalarAsync())! == 0)
            {
                return true;
            }

            await Task.Delay(50);
        }

        return false;
    }

    private static async Task<IReadOnlyList<BlockedBackend>> ReadAsync(NpgsqlConnection admin, string database, string appUser)
    {
        const string activitySql = """
            SELECT pid, state, wait_event_type, wait_event, backend_xid::text, left(query, 160)
            FROM pg_stat_activity
            WHERE datname = @db AND usename = @user AND wait_event_type = 'Lock'
            ORDER BY backend_start
            """;
        var rows = new List<(int Pid, string? State, string? Type, string? Event, string? Xid, string Query)>();
        await using (var command = new NpgsqlCommand(activitySql, admin))
        {
            command.Parameters.AddWithValue("db", database);
            command.Parameters.AddWithValue("user", appUser);
            await using var reader = await command.ExecuteReaderAsync();
            while (await reader.ReadAsync())
            {
                rows.Add((reader.GetInt32(0),
                    reader.IsDBNull(1) ? null : reader.GetString(1),
                    reader.IsDBNull(2) ? null : reader.GetString(2),
                    reader.IsDBNull(3) ? null : reader.GetString(3),
                    reader.IsDBNull(4) ? null : reader.GetString(4),
                    reader.GetString(5)));
            }
        }

        const string lockSql = """
            SELECT l.locktype, coalesce(c.relname, ''), l.mode, l.granted
            FROM pg_locks l
            LEFT JOIN pg_class c ON c.oid = l.relation
            LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE l.pid = @pid AND (l.locktype = 'transactionid' OR n.nspname = 'eledgercare')
            ORDER BY l.granted DESC, l.locktype, c.relname
            """;
        var result = new List<BlockedBackend>();
        foreach (var row in rows)
        {
            var locks = new List<LockRow>();
            await using var command = new NpgsqlCommand(lockSql, admin);
            command.Parameters.AddWithValue("pid", row.Pid);
            await using var reader = await command.ExecuteReaderAsync();
            while (await reader.ReadAsync())
            {
                locks.Add(new LockRow(reader.GetString(0), reader.GetString(1), reader.GetString(2), reader.GetBoolean(3)));
            }

            result.Add(new BlockedBackend(row.Pid, row.State, row.Type, row.Event, row.Xid, row.Query, locks));
        }

        return result;
    }
}

/// <summary>Wraps bytes in a non-seekable stream so HttpClient must use chunked transfer encoding.</summary>
public sealed class NonSeekableStream(byte[] data) : Stream
{
    private int position;

    public override bool CanRead => true;

    public override bool CanSeek => false;

    public override bool CanWrite => false;

    public override long Length => throw new NotSupportedException();

    public override long Position
    {
        get => throw new NotSupportedException();
        set => throw new NotSupportedException();
    }

    public override int Read(byte[] buffer, int offset, int count)
    {
        var take = Math.Min(count, data.Length - position);
        Array.Copy(data, position, buffer, offset, take);
        position += take;
        return take;
    }

    public override void Flush()
    {
    }

    public override long Seek(long offset, SeekOrigin origin) => throw new NotSupportedException();

    public override void SetLength(long value) => throw new NotSupportedException();

    public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
}
