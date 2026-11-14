using System.Globalization;
using System.Security.Cryptography;
using System.Text;

namespace ELedgerCare.Tests.Shared;

/// <summary>
/// Deterministic, source-first generator for small synthetic PDFs used by F1 tests. Output contains
/// only fictitious text, uses the standard-14 Helvetica font (no embedded or system font needed),
/// no timestamps and correct cross-reference offsets. Variants deliberately introduce one structural
/// defect at a time while keeping every other offset valid, so a rejection is attributable.
/// Independent of the R&D corpus. Written for WP-0003 by eld-implementer.
/// </summary>
public static class SyntheticPdf
{
    public const string FixtureId = "F1-SWO-001";

    public sealed record Spec
    {
        public int Pages { get; init; } = 1;

        public string Header { get; init; } = "%PDF-1.4";

        /// <summary>Overrides the /Kids array content, e.g. "99 0 R".</summary>
        public string? KidsOverride { get; init; }

        /// <summary>Overrides the /Count value in the page tree.</summary>
        public int? CountOverride { get; init; }

        /// <summary>Overrides the trailer /Root reference, e.g. "99 0 R".</summary>
        public string? RootOverride { get; init; }

        /// <summary>Removes "endobj" and the closing "&gt;&gt;" from the first page object.</summary>
        public bool BreakFirstPageObject { get; init; }

        /// <summary>Keeps the declared /Length of the first content stream but writes only half of its data.</summary>
        public bool TruncateFirstContentStream { get; init; }

        /// <summary>Adds a constant to every in-use xref entry offset (startxref unchanged).</summary>
        public int XrefEntryShift { get; init; }

        /// <summary>Adds a constant to the startxref value (entries unchanged).</summary>
        public int StartXrefShift { get; init; }

        public string? UserPassword { get; init; }

        public string? OwnerPassword { get; init; }

        public bool Encrypted => UserPassword is not null || OwnerPassword is not null;
    }

    /// <summary>The canonical one-page product fixture.</summary>
    public static byte[] CanonicalFixture() => Build(new Spec());

    public static byte[] Build(Spec spec)
    {
        ArgumentNullException.ThrowIfNull(spec);
        var objects = new List<byte[]>();
        int Reserve()
        {
            objects.Add([]);
            return objects.Count;
        }

        var catalog = Reserve();
        var pagesNode = Reserve();
        var font = Reserve();
        var pageIds = new List<int>();
        var contentIds = new List<int>();
        for (var i = 0; i < spec.Pages; i++)
        {
            pageIds.Add(Reserve());
            contentIds.Add(Reserve());
        }

        var encryptId = spec.Encrypted ? Reserve() : 0;
        var fileId = MD5.HashData(Encoding.ASCII.GetBytes($"eledgercare-{FixtureId}-pages-{spec.Pages}"));
        var security = spec.Encrypted
            ? StandardSecurity.Create(spec.UserPassword ?? string.Empty, spec.OwnerPassword ?? spec.UserPassword ?? string.Empty, fileId)
            : null;

        objects[catalog - 1] = Ascii($"<< /Type /Catalog /Pages {pagesNode} 0 R >>");
        var kids = spec.KidsOverride ?? string.Join(' ', pageIds.Select(id => $"{id} 0 R"));
        objects[pagesNode - 1] = Ascii($"<< /Type /Pages /Kids [{kids}] /Count {spec.CountOverride ?? spec.Pages} >>");
        objects[font - 1] = Ascii("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>");

        for (var i = 0; i < spec.Pages; i++)
        {
            var page = $"<< /Type /Page /Parent {pagesNode} 0 R /MediaBox [0 0 612 792] " +
                       $"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {contentIds[i]} 0 R >>";
            if (i == 0 && spec.BreakFirstPageObject)
            {
                page = page[..^2];
            }

            objects[pageIds[i] - 1] = Ascii(page);

            var text = string.Create(CultureInfo.InvariantCulture,
                $"BT /F1 14 Tf 72 720 Td (eLedgerCare synthetic fixture {FixtureId} page {i + 1} of {spec.Pages}) Tj ")
                + "0 -22 Td (Fictitious maintenance work order WO-0001: replace hallway light fixture.) Tj "
                + "0 -22 Td (Not a real document. Contains no customer data.) Tj ET";
            var stream = Encoding.ASCII.GetBytes(text);
            if (security is not null)
            {
                stream = security.EncryptObjectData(contentIds[i], 0, stream);
            }

            objects[contentIds[i] - 1] = Concat(
                Ascii($"<< /Length {stream.Length} >>\nstream\n"),
                i == 0 && spec.TruncateFirstContentStream ? stream[..(stream.Length / 2)] : stream,
                Ascii("\nendstream"));
        }

        if (security is not null)
        {
            objects[encryptId - 1] = Ascii(
                $"<< /Filter /Standard /V 1 /R 2 /O <{Convert.ToHexString(security.O)}> " +
                $"/U <{Convert.ToHexString(security.U)}> /P {security.P} >>");
        }

        using var output = new MemoryStream();
        Write(output, Ascii(spec.Header + "\n"));
        Write(output, [0x25, 0xE2, 0xE3, 0xCF, 0xD3, 0x0A]);
        var offsets = new List<long>();
        for (var i = 0; i < objects.Count; i++)
        {
            offsets.Add(output.Position);
            var body = objects[i];
            Write(output, Ascii($"{i + 1} 0 obj\n"));
            Write(output, body);
            var breakThis = spec.BreakFirstPageObject && pageIds.Count > 0 && i + 1 == pageIds[0];
            Write(output, Ascii(breakThis ? "\n" : "\nendobj\n"));
        }

        var xrefOffset = output.Position;
        var xref = new StringBuilder();
        xref.Append(CultureInfo.InvariantCulture, $"xref\n0 {objects.Count + 1}\n0000000000 65535 f \n");
        foreach (var offset in offsets)
        {
            xref.Append(CultureInfo.InvariantCulture, $"{offset + spec.XrefEntryShift:D10} 00000 n \n");
        }

        var idHex = Convert.ToHexString(fileId);
        var root = spec.RootOverride ?? $"{catalog} 0 R";
        var encrypt = security is not null ? $" /Encrypt {encryptId} 0 R" : string.Empty;
        xref.Append(CultureInfo.InvariantCulture,
            $"trailer\n<< /Size {objects.Count + 1} /Root {root}{encrypt} /ID [<{idHex}> <{idHex}>] >>\n");
        xref.Append(CultureInfo.InvariantCulture, $"startxref\n{xrefOffset + spec.StartXrefShift}\n%%EOF\n");
        Write(output, Ascii(xref.ToString()));
        return output.ToArray();
    }

    private static byte[] Ascii(string text) => Encoding.ASCII.GetBytes(text);

    private static void Write(Stream stream, byte[] bytes) => stream.Write(bytes, 0, bytes.Length);

    private static byte[] Concat(params byte[][] parts) => parts.SelectMany(p => p).ToArray();

    /// <summary>PDF standard security handler, revision 2 (40-bit RC4), ISO 32000-1 algorithms 2, 3 and 4.</summary>
    private sealed class StandardSecurity
    {
        private static readonly byte[] Padding =
        [
            0x28, 0xBF, 0x4E, 0x5E, 0x4E, 0x75, 0x8A, 0x41, 0x64, 0x00, 0x4E, 0x56, 0xFF, 0xFA, 0x01, 0x08,
            0x2E, 0x2E, 0x00, 0xB6, 0xD0, 0x68, 0x3E, 0x80, 0x2F, 0x0C, 0xA9, 0xFE, 0x64, 0x53, 0x69, 0x7A,
        ];

        private readonly byte[] key;

        private StandardSecurity(byte[] o, byte[] u, int p, byte[] key)
        {
            O = o;
            U = u;
            P = p;
            this.key = key;
        }

        public byte[] O { get; }

        public byte[] U { get; }

        public int P { get; }

        public static StandardSecurity Create(string userPassword, string ownerPassword, byte[] fileId)
        {
            const int permissions = -44;
            var ownerKey = MD5.HashData(Pad(ownerPassword))[..5];
            var o = Rc4(ownerKey, Pad(userPassword));
            var p = BitConverter.GetBytes(permissions);
            var key = MD5.HashData(Concat(Pad(userPassword), o, p, fileId))[..5];
            var u = Rc4(key, Padding);
            return new StandardSecurity(o, u, permissions, key);
        }

        public byte[] EncryptObjectData(int objectNumber, int generation, byte[] data)
        {
            var objectKey = MD5.HashData(Concat(
                key,
                [(byte)objectNumber, (byte)(objectNumber >> 8), (byte)(objectNumber >> 16)],
                [(byte)generation, (byte)(generation >> 8)]))[..Math.Min(key.Length + 5, 16)];
            return Rc4(objectKey, data);
        }

        private static byte[] Pad(string password)
        {
            var bytes = Encoding.Latin1.GetBytes(password);
            return bytes.Concat(Padding).Take(32).ToArray();
        }

        private static byte[] Rc4(byte[] rc4Key, byte[] data)
        {
            var s = Enumerable.Range(0, 256).Select(i => (byte)i).ToArray();
            for (int i = 0, j = 0; i < 256; i++)
            {
                j = (j + s[i] + rc4Key[i % rc4Key.Length]) & 0xFF;
                (s[i], s[j]) = (s[j], s[i]);
            }

            var result = new byte[data.Length];
            for (int n = 0, i = 0, j = 0; n < data.Length; n++)
            {
                i = (i + 1) & 0xFF;
                j = (j + s[i]) & 0xFF;
                (s[i], s[j]) = (s[j], s[i]);
                result[n] = (byte)(data[n] ^ s[(s[i] + s[j]) & 0xFF]);
            }

            return result;
        }
    }
}
