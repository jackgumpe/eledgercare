def _uocr_page_count_guard(logits, gen_ids, expected_pages, page_id, eos_id, max_page_tokens, st):
    """vLLM unlimited_sparse_plugin.page_count_guard._PageCountGuard (per-step, in place)."""
    if expected_pages <= 0:
        return logits
    n = len(gen_ids)
    if n > st['scanned']:
        tail = gen_ids[st['scanned']:n]
        m = tail.count(page_id)
        if m:
            st['marker_cum'] += m
            st['page_len'] = tail[::-1].index(page_id)
        else:
            st['page_len'] += len(tail)
        st['scanned'] = n
    mc = st['marker_cum']
    if mc > expected_pages:
        keep = logits[eos_id].clone(); logits[:] = -float('inf'); logits[eos_id] = keep
    elif 0 < max_page_tokens <= st['page_len']:
        tid = page_id if mc < expected_pages else eos_id
        keep = logits[tid].clone(); logits[:] = -float('inf'); logits[tid] = keep
    elif mc < expected_pages:
        logits[eos_id] = -float('inf')
    return logits


def _uocr_no_repeat_ngram(logits, gen_ids, ngram_size, window_size, whitelist):
    """vLLM deepseek_ocr.NoRepeatNGramLogitsProcessor (on generated ids only)."""
    if ngram_size <= 0 or len(gen_ids) < ngram_size:
        return logits
    prefix = tuple(gen_ids[-(ngram_size - 1):]) if ngram_size > 1 else tuple()
    start = max(0, len(gen_ids) - window_size)
    end = len(gen_ids) - ngram_size + 1
    banned = set()
    for i in range(start, end):
        ng = tuple(gen_ids[i:i + ngram_size])
        if ng[:-1] == prefix:
            banned.add(ng[-1])
    banned -= whitelist
    if banned:
        logits[list(banned)] = -float('inf')
    return logits
