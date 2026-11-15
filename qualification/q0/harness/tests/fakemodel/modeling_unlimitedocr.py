# CPU test double of the pinned entry module. It mirrors the native names, call graph and
# return contract that the harness observes; it contains no model and no torch.
from .modeling_deepseekv2 import DeepseekV2Model, configure_dash_inference
from .configuration_deepseek_v2 import DeepseekV2Config
try:
    from .sparse_gather_triton import SPARSE_BLOCK_SIZE_SENTINEL as _sgt_sentinel  # noqa: F401
except Exception:
    pass
from .dash_attention import DashAttention  # noqa: F401
try:
    from .sparse_gather_e2e_triton import triton_gather_attention_e2e as _dash_e2e_copy_hint  # noqa: F401
except Exception:
    pass
import time

PAGE = 128827
IMG = 128815
EOS = 1


def extract_coordinates_and_label(ref_text, image_width, image_height):
    try:
        label_type = ref_text[1]
        cor_list = eval(ref_text[2])
    except Exception as e:
        print(e)
        return None
    return (label_type, cor_list)


def draw_bounding_boxes(image, refs, ouput_path, image_prefix=''):
    for ref in refs:
        try:
            extract_coordinates_and_label(ref, 1, 1)
        except:  # noqa: E722  (native code swallows everything here)
            continue
    return image


def process_image_with_refs(image, ref_texts, output_path, image_prefix=''):
    return draw_bounding_boxes(image, ref_texts, output_path, image_prefix=image_prefix)


class DynamicCache:
    def __init__(self):
        self.key_cache = []
        self.value_cache = []


class FakeTensor:
    def __init__(self, shape, itemsize=2):
        self.shape = tuple(shape)
        self._itemsize = itemsize

    def numel(self):
        n = 1
        for d in self.shape:
            n *= d
        return n

    def element_size(self):
        return self._itemsize


class _Out:
    def __init__(self, past_key_values):
        self.past_key_values = past_key_values
        self.last_hidden_state = None


class FakeTokenizer:
    eos_token_id = EOS

    def encode(self, text, add_special_tokens=False):
        out = []
        for part in text.replace('<PAGE>', ' <PAGE> ').split():
            out.append(PAGE if part == '<PAGE>' else 1000 + (sum(map(ord, part)) % 5000))
        return out

    def decode(self, ids, skip_special_tokens=False):
        return ''.join('<PAGE>' if i == PAGE else f'[{i}]' for i in ids)


class UnlimitedOCRConfig(DeepseekV2Config):
    model_type = "unlimited-ocr"


class UnlimitedOCRModel(DeepseekV2Model):
    def forward(self, input_ids=None, past_key_values=None, **kw):
        cache = past_key_values
        n = len(input_ids)
        seq = (cache.key_cache[0].shape[-2] if cache.key_cache else 0) + n
        cache.key_cache = [FakeTensor((1, 10, seq, 128)) for _ in range(12)]
        cache.value_cache = [FakeTensor((1, 10, seq, 128)) for _ in range(12)]
        if n > 1:
            self.layer.prefill(cache)
        else:
            self.layer.decode(cache)
        return _Out(cache)


class UnlimitedOCRForCausalLM:
    def __init__(self, config):
        self.config = config
        self.model = UnlimitedOCRModel(config)
        self.flaky = False
        self.force_length = False
        self.calls = 0

    def infer(self, tokenizer, prompt='', image_file='', output_path='', base_size=1024, image_size=640,
              crop_mode=None, test_compress=False, save_results=False, eval_mode=False, max_length=131072,
              max_new_tokens=None, tps_interval=0, no_repeat_ngram_size=0, ngram_window=0,
              ngram_whitelist_token_ids=None, temperature=0.0, page_count_guard=True,
              max_page_tokens=20000, dash_topm=16, max_crops=16, return_dict=False):
        images = list(image_file)
        n_img = len(images)
        prompt = '<PAGE><image>' * n_img + prompt
        ids = [0]
        for _ in range(n_img):
            ids += [PAGE] + [IMG] * 273
        ids += tokenizer.encode(prompt.replace('<PAGE><image>', ''))
        res = self._uocr_generate(tokenizer, ids, n_img, max_new_tokens=max_new_tokens, max_length=max_length)
        outputs = res['text']
        if save_results and output_path:
            self._uocr_save_results(outputs, images, output_path)
        if return_dict:
            res['prompt'] = prompt
            return res
        return outputs

    def infer_multi(self, tokenizer, prompt='', image_files=None, output_path='', image_size=640,
                    save_results=False, max_length=131072, tps_interval=0, no_repeat_ngram_size=0,
                    ngram_window=0, temperature=0.0, **kwargs):
        kwargs.setdefault('crop_mode', False)
        res = self.infer(tokenizer, prompt=prompt, image_file=list(image_files), output_path=output_path,
                         image_size=image_size, save_results=save_results, max_length=max_length,
                         tps_interval=tps_interval, no_repeat_ngram_size=no_repeat_ngram_size,
                         ngram_window=ngram_window, temperature=temperature, return_dict=True, **kwargs)
        return res['text'], len(res['token_ids'])

    def _uocr_generate(self, tokenizer, input_ids, n_pages, max_new_tokens=16384, max_length=131072):
        cfg = self.config
        saved_cfg = (cfg._ring_window, cfg.sliding_window)
        cfg._ring_window = None
        cfg.sliding_window = None
        state = configure_dash_inference(self.model, True)
        self.calls += 1
        t0 = time.time()
        try:
            cache = DynamicCache()
            self.model.forward(input_ids=input_ids, past_key_values=cache)
            t_first = time.time()
            script = []
            for p in range(n_pages):
                script += [PAGE, 7, 8, 9 + p]
            if self.flaky and self.calls == 5:  # second warm repeat of the first fixture differs
                script[-1] = 4242
            gen, finish = [], 'length'
            for step in range(max_new_tokens):
                nxt = script[step] if step < len(script) else (2 if self.force_length else EOS)
                if nxt == EOS:
                    finish = 'stop'
                    break
                gen.append(nxt)
                self.model.forward(input_ids=[nxt], past_key_values=cache)
        finally:
            configure_dash_inference(self.model, False, state=state)
            cfg._ring_window, cfg.sliding_window = saved_cfg
        return {'text': tokenizer.decode(gen), 'token_ids': gen, 'prompt_token_ids': list(input_ids),
                'finish_reason': finish, 'num_pages_out': gen.count(PAGE),
                'expected_pages': list(input_ids).count(PAGE), 'time': time.time() - t0,
                'prefill_time': t_first - t0}

    def _uocr_save_results(self, outputs, images, output_path):
        process_image_with_refs(None, [(outputs, 'x', '[1,2,3,4]')], output_path)
