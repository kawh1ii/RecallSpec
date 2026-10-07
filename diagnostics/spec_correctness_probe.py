"""Fresh-process, fixed-config greedy output comparison for RecallSpec."""

import argparse
import json
from pathlib import Path
import sys
import time

from vllm import LLM, SamplingParams

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from benchmark import prompts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("base", "native", "shared"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=-1,
                        help="-1 leaves vLLM and SamplingParams defaults unchanged")
    parser.add_argument("--repeat", type=int, default=2)
    parser.add_argument("--logprobs", type=int, default=-1,
                        help="-1 does not request logprobs")
    parser.add_argument("--warmup", action="store_true",
                        help="Run the original benchmark's variant 0 first")
    args = parser.parse_args()

    spec = None if args.mode == "base" else {
        "method": "ngram", "num_speculative_tokens": 8,
        "prompt_lookup_min": 2, "prompt_lookup_max": 5,
    }
    llm_options = {"model": args.model, "dtype": "bfloat16",
                   "max_model_len": 2048, "gpu_memory_utilization": 0.75,
                   "max_num_seqs": 8, "enable_prefix_caching": False,
                   "speculative_config": spec}
    if args.seed >= 0:
        llm_options["seed"] = args.seed
    llm = LLM(**llm_options)
    sampling_options = {"temperature": 0, "max_tokens": 128,
                        "min_tokens": 128, "ignore_eos": True}
    if args.seed >= 0:
        sampling_options["seed"] = args.seed
    if args.logprobs >= 0:
        sampling_options["logprobs"] = args.logprobs
    sampling = SamplingParams(**sampling_options)
    if args.warmup:
        llm.generate(prompts("unique_general", 1, 0), sampling, use_tqdm=False)
    records = []
    for repetition in range(args.repeat):
        for variant in range(1, 9):
            prompt = prompts("unique_general", 1, variant)[0]
            start = time.perf_counter()
            output = llm.generate([prompt], sampling, use_tqdm=False)[0].outputs[0]
            top = []
            for entry in output.logprobs or []:
                top.append({str(token): value.logprob
                            for token, value in (entry or {}).items()})
            records.append({"repetition": repetition, "variant": variant,
                            "prompt": prompt,
                            "elapsed_seconds": time.perf_counter() - start,
                            "token_ids": output.token_ids,
                            "top_logprobs": top})
            print(args.mode, repetition, variant, len(output.token_ids), flush=True)
    args.output.write_text(json.dumps({"mode": args.mode, "seed": args.seed,
                                       "warmup": args.warmup,
                                       "logprobs": args.logprobs,
                                       "records": records}, indent=2))


if __name__ == "__main__":
    main()
