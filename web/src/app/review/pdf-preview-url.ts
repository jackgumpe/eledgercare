import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';

const canonicalUuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const strictSameOriginPreviewRegex =
  /^\/api\/documents\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\/preview(?:#page=[1-3])?$/;
const zeroUuid = '00000000-0000-0000-0000-000000000000';

/**
 * Narrowly scoped URL builder & sanitizer gate for the native browser PDF preview pane (F3-BIC-04).
 * Accepts exclusively same-origin `/api/documents/<canonical-lowercase-uuid>/preview(#page=<1..3>)?`.
 * Rejects empty UUIDs, upper/mixed case, non-preview paths, query strings, external origins, or page numbers outside 1..3.
 */
export function buildRelativePdfPreviewHref(documentId: string, pageNumber?: number): string {
  const normalizedId = documentId.trim().toLowerCase();
  if (!canonicalUuidRegex.test(normalizedId) || normalizedId === zeroUuid) {
    throw new Error('Invalid canonical document UUID for PDF preview URL.');
  }

  let href = `/api/documents/${normalizedId}/preview`;
  if (pageNumber !== undefined) {
    if (!Number.isInteger(pageNumber) || pageNumber < 1 || pageNumber > 3) {
      throw new Error('PDF preview pageNumber must be an integer within 1..3.');
    }
    href += `#page=${pageNumber}`;
  }

  if (!strictSameOriginPreviewRegex.test(href)) {
    throw new Error('Constructed PDF preview URL failed strict pattern validation.');
  }

  return href;
}

export function trustSameOriginPdfPreviewUrl(
  sanitizer: DomSanitizer,
  documentId: string,
  pageNumber?: number,
): SafeResourceUrl {
  const href = buildRelativePdfPreviewHref(documentId, pageNumber);
  return sanitizer.bypassSecurityTrustResourceUrl(href);
}
