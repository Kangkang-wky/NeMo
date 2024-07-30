# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Use this file to create a lexicon file for Flashlight decoding from an existing KenLM arpa file
# A lexicon file is required for Flashlight decoding in most cases, as it acts as a map from the words
# in you arpa file to the representation used by your ASR AM.
# For more details, see: https://github.com/flashlight/flashlight/tree/main/flashlight/app/asr#data-preparation
#
# Usage: python create_lexicon_from_arpa.py --arpa /path/to/english.arpa --model /path/to/model.nemo --lower
#
#


import argparse
import os
import re

from nemo.collections.common.tokenizers.aggregate_tokenizer import AggregateTokenizer
from nemo.utils import logging


def save(arpa, lexicon_file, lower, tokenizer, langid):
    if not os.path.exists(arpa):
        logging.critical(f"ARPA file [ {arpa} ] not detected on disk, aborting!")
        exit(255)

    logging.info(f"Writing Lexicon file to: {lexicon_file}...")
    with open(lexicon_file, "w", encoding='utf_8', newline='\n') as f:
        with open(arpa, "r", encoding='utf_8') as arpa_f:
            for line in arpa_f:
                # verify if the line corresponds to unigram
                if not re.match(r"[-]*[0-9\.]+\t\S+\t*[-]*[0-9\.]*$", line):
                    continue
                word = line.split("\t")[1]
                word = word.strip().lower() if lower else word.strip()
                if word == "<UNK>" or word == "<unk>" or word == "<s>" or word == "</s>":
                    continue

                if tokenizer is None:
                    f.write("{w}\t{s}\n".format(w=word, s=" ".join(word)))
                else:
                    if isinstance(tokenizer, AggregateTokenizer):
                        if not langid:
                            raise ValueError("--langid must be set for model with AggregateTokenizer")
                        w_ids = tokenizer.text_to_ids(word, lang_id=langid)
                        f.write(
                            "{w}\t{s}\n".format(w=word, s=" ".join(tokenizer.text_to_tokens(word, lang_id=langid)))
                        )
                    else:
                        w_ids = tokenizer.text_to_ids(word)
                        if tokenizer.unk_id not in w_ids:
                            f.write("{w}\t{s}\n".format(w=word, s=" ".join(tokenizer.text_to_tokens(word))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Utility script for generating lexicon file from a KenLM arpa file")
    parser.add_argument("--arpa", required=True, help="path to your arpa file")
    parser.add_argument("--dst", help="directory to store generated lexicon", default=None)
    parser.add_argument("--lower", action='store_true', help="Whether to lowercase the arpa vocab")
    parser.add_argument("--model", default=None, help="path to Nemo model for its tokeniser")
    parser.add_argument("--langid", default=None, help="lang_id for model with AggregateTokenizer")

    args = parser.parse_args()

    if args.dst is not None:
        save_path = args.dst
    else:
        save_path = os.path.dirname(args.arpa)
    os.makedirs(save_path, exist_ok=True)
    lexicon_file = os.path.join(save_path, os.path.splitext(os.path.basename(args.arpa))[0] + '.lexicon')

    tokenizer = None
    if args.model is not None:
        from nemo.collections.asr.models import ASRModel

        asr_model = ASRModel.restore_from(restore_path=args.model, map_location='cpu')
        if hasattr(asr_model, 'tokenizer'):
            tokenizer = asr_model.tokenizer
        else:
            logging.warning('Supplied Nemo model does not contain a tokenizer')
    save(arpa=args.arpa, lexicon_file=lexicon_file, lower=args.lower, tokenizer=tokenizer, langid=args.langid)
