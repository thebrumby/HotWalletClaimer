"""Seed phrase input validation and local retrieval."""

import os
import re
import getpass


class WalletMixin:
    """Seed phrase input validation and local retrieval. Uses the shared state on Claimer."""

    def validate_seed_phrase(self, allowed_lengths=(12, 13)):
        """
        Prompt the user for a seed phrase and validate it.
    
        - Accepts 12 or 13 words by default (configurable via allowed_lengths).
        - Normalizes input: lowercases, strips extra whitespace, and splits on spaces.
        - Returns the normalized seed phrase (words joined with single spaces).
        """
        lengths_str = "/".join(str(n) for n in allowed_lengths)
    
        while True:
            prompt = f"Step {self.step} - Please enter your {lengths_str}-word seed phrase"
            phrase_raw = (
                getpass.getpass(prompt + " (your input is hidden): ")
                if self.settings.get('hideSensitiveInput')
                else input(prompt + " (your input is visible): ")
            )
    
            try:
                if not phrase_raw or not phrase_raw.strip():
                    raise ValueError("Seed phrase cannot be empty.")
    
                # Normalize: lowercase, strip, split by whitespace
                words = phrase_raw.strip().lower().split()
    
                # Length check
                if len(words) not in allowed_lengths:
                    raise ValueError(
                        f"Seed phrase must contain exactly {lengths_str} words (got {len(words)})."
                    )
    
                # Character check (letters only)
                if not all(re.fullmatch(r"[a-z]+", w) for w in words):
                    raise ValueError("Seed phrase may only contain letters a–z.")
    
                # Success: store normalized phrase
                self.seed_phrase = " ".join(words)
                return self.seed_phrase
    
            except ValueError as e:
                # Keep logs safe—don’t echo the phrase itself
                self.output(f"Error: {e}", 1)

    def get_seed_phrase_from_file(self, screenshots_path):
        seed_file_path = os.path.join(screenshots_path, 'seed.txt')
        if os.path.exists(seed_file_path):
            with open(seed_file_path, 'r') as file:
                return file.read().strip()
        return None
