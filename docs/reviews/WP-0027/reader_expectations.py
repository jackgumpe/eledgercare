"""Independent fixtures specified before either WP-0027 reader or evidence was seen.

The adapter supplies authenticated source pages and tokenizer-native encodings.
Labels name distinct visible source content, including an entire Unicode block.
A = ordinary acceptance, E = exceptional acceptance, U = unresolved.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Case:
    name: str
    sections: tuple
    source: tuple = ("p", "q", "r")
    eos: bool = True
    binding: str = "authentic"
    allowed: str = "U"

CASES = (
    Case("three ordinary", ("p","q","r"), allowed="A"),
    Case("one redundant terminal", ("p","q","r","empty"), allowed="E"),
    Case("blank second physical page", ("p","empty","r"), ("p","empty","r"), allowed="AU"),
    Case("blank source plus redundant fourth", ("p","empty","r","empty"), ("p","empty","r")),
    Case("interior fourth delimiter", ("p","empty","q","r")),
    Case("two trailing delimiters", ("p","q","r","empty","empty")),
    Case("fourth visible block", ("p","q","r","s")),
    Case("fourth literal text", ("p","q","r","literal")),
    Case("fourth space", ("p","q","r","space")),
    Case("fourth newline", ("p","q","r","newline")),
    Case("fourth invisible markup", ("p","q","r","markup")),
    Case("missing section", ("p","r")),
    Case("merged sections", ("p","qr","empty")),
    Case("merged plus extra", ("p","qr","empty","empty")),
    Case("substitute one duplicate", ("p","q","q")),
    Case("duplicate plus extra", ("p","q","q","empty")),
    Case("reordered plus extra", ("q","p","r","empty")),
    Case("lost source line plus extra", ("p","q_partial","r","empty")),
    Case("extra ungrounded block inside plus extra", ("p","q_unmapped","r","empty")),
    Case("no EOS", ("p","q","r","empty"), eos=False),
    Case("different third physical identity", ("p","q","r","empty"), binding="foreign_page"),
    Case("same page count wrong order", ("p","q","r","empty"), binding="wrong_order"),
    Case("wrong PDF identity", ("p","q","r","empty"), binding="foreign_pdf"),
)
# On A/E compare original-page numbers, source hashes, spans, pages and every
# original char/byte/token selection against the unaltered three-section parser.
# Original through-EOS stream remains immutable. Verify raw marker byte offset
# and exact token position of the discarded delimiter in each accepted E.
