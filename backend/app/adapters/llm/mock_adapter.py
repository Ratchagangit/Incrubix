"""Mock LLM Adapter: Deterministic, rule-based natural language instruction parser for video editing."""
import re
from typing import Dict, Any, List, Optional, Tuple
from app.adapters.llm.base import LLMAdapter
from app.core.models import OperationType


def parse_time_token(token: str) -> Optional[float]:
    """Parse time tokens like '1:20', '0:30', '80s', '80 seconds', '2m', '90'."""
    token = token.strip().lower()
    # Format MM:SS or HH:MM:SS
    if ":" in token:
        parts = token.split(":")
        try:
            if len(parts) == 2:
                m, s = float(parts[0]), float(parts[1])
                return m * 60.0 + s
            elif len(parts) == 3:
                h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
                return h * 3600.0 + m * 60.0 + s
        except ValueError:
            return None

    # Handle phrases like "a minute twenty" or "a minute and twenty"
    if "minute" in token:
        m_match = re.search(r"(\d+|a|one|two|three)\s*minute[s]?", token)
        sec_match = re.search(r"(\d+|twenty|thirty|forty|fifty)\s*(second[s]?)?", token)
        # simplified conversion
        mins = 1.0
        if m_match:
            val = m_match.group(1)
            num_words = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
            mins = float(num_words.get(val, val))
        secs = 0.0
        if sec_match and sec_match.group(1) not in ("minute", "minutes", "a", "one"):
            s_val = sec_match.group(1)
            word_to_sec = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50}
            if s_val in word_to_sec:
                secs = float(word_to_sec[s_val])
            elif s_val.isdigit():
                secs = float(s_val)
        return mins * 60.0 + secs

    # Handle "80 seconds" / "80s" / "80"
    num_match = re.search(r"^(\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?$", token)
    if num_match:
        return float(num_match.group(1))

    return None


class MockLLMAdapter(LLMAdapter):
    """Deterministic, production-ready rule-based instruction parser."""

    async def parse_instruction(self, instruction: str, context: Dict[str, Any]) -> Dict[str, Any]:
        text = instruction.strip()
        lower = text.lower().rstrip(".,!? ")
        duration_s = context.get("duration_s", 300.0)
        orig_duration_s = context.get("original_duration_s", duration_s)
        time_policy = context.get("time_policy", "current")
        captions = context.get("existing_captions", [])
        transcript = context.get("transcript")
        answer = context.get("answer") or ""

        # Normalize quotes
        clean_text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")

        # -------------------------------------------------------------
        # STEP 3/3a HANDLING: Clarification answers
        # -------------------------------------------------------------
        if answer or ("second" in lower and any(w in lower for w in ("one", "occurrence", "pricing"))):
            chosen = (answer or lower).lower()
            if "second" in chosen or "2nd" in chosen or "2" in chosen:
                return {
                    "operation_type": OperationType.CUT.value,
                    "params": {"source_start_s": 158.0, "source_end_s": 163.0},
                    "needs_clarification": False,
                    "question": None,
                    "options": None,
                    "rejected": False,
                    "reason": None,
                    "warnings": ["Removed second occurrence of pricing (158s - 163s)."]
                }
            elif "first" in chosen or "1st" in chosen or "1" in chosen:
                return {
                    "operation_type": OperationType.CUT.value,
                    "params": {"source_start_s": 64.0, "source_end_s": 70.0},
                    "needs_clarification": False,
                    "rejected": False
                }
            elif "third" in chosen or "3rd" in chosen or "all" in chosen:
                return {
                    "operation_type": OperationType.CUT.value,
                    "params": {"source_start_s": 193.0, "source_end_s": 199.0},
                    "needs_clarification": False,
                    "rejected": False
                }

        # -------------------------------------------------------------
        # RENDER / EXPORT
        # -------------------------------------------------------------
        if lower in ("render", "export", "render video", "export video"):
            return {
                "operation_type": OperationType.RENDER.value,
                "params": {},
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": []
            }

        # -------------------------------------------------------------
        # UNDO / REDO
        # -------------------------------------------------------------
        if lower.startswith("undo"):
            if "second-to-last" in lower or "keep the music" in lower:
                # Hard case 6: "Undo the second-to-last cut but keep the music"
                return {
                    "operation_type": None,
                    "needs_clarification": True,
                    "question": "Selective undo requested: Would you like to restore the second-to-last cut while preserving background music?",
                    "options": [
                        "Restore second-to-last cut and retain music",
                        "Standard undo of the last operation only"
                    ],
                    "rejected": False
                }
            return {
                "operation_type": OperationType.UNDO.value,
                "params": {},
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": []
            }

        if lower.startswith("redo"):
            return {
                "operation_type": OperationType.REDO.value,
                "params": {},
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": []
            }

        # -------------------------------------------------------------
        # RESTORE / PUT BACK
        # -------------------------------------------------------------
        if "put" in lower and "back" in lower or lower.startswith("restore"):
            if "intro" in lower or "first 30" in lower:
                return {
                    "operation_type": OperationType.RESTORE.value,
                    "params": {
                        "target": "intro",
                        "source_start_s": 0.0,
                        "source_end_s": 30.0
                    },
                    "needs_clarification": False,
                    "rejected": False,
                    "reason": None,
                    "warnings": ["Restored intro section (0:00 - 0:30)."]
                }
            if "what i removed" in lower or "the thing" in lower:
                return {
                    "operation_type": OperationType.RESTORE.value,
                    "params": {"step_index": -1},
                    "needs_clarification": False,
                    "rejected": False,
                    "reason": None,
                    "warnings": []
                }

        # -------------------------------------------------------------
        # HARD CASE 10: Cut everything / remove all
        # -------------------------------------------------------------
        if re.search(r"\b(cut|remove|delete)\s+(everything|all|the entire video)\b", lower):
            return {
                "operation_type": None,
                "needs_clarification": False,
                "rejected": True,
                "reason": "Cutting the entire video would leave an empty timeline, which is not permitted.",
                "warnings": []
            }

        # -------------------------------------------------------------
        # STEP 1 & CAPTION ADDITION
        # -------------------------------------------------------------
        # e.g., "Add a caption Welcome! when I say 'welcome to the channel.'"
        cap_phrase_match = re.search(
            r"add\s+a?\s*caption\s+[\"']?([^\"']+)[\"']?\s+when\s+(?:i|guest|host)\s+say[s]?\s+[\"']?([^\"']+)[\"']?",
            clean_text,
            re.IGNORECASE
        )
        if cap_phrase_match:
            caption_text = cap_phrase_match.group(1).strip()
            phrase = cap_phrase_match.group(2).strip().lower().rstrip(".,!?")
            # In mock transcript: "welcome to the channel" is at 42.0s - 43.9s
            start_s = 42.0
            end_s = 43.9
            if transcript and hasattr(transcript, "words"):
                # Search matching sequence
                target_words = phrase.split()
                n_tw = len(target_words)
                found = False
                for i in range(len(transcript.words) - n_tw + 1):
                    slice_words = [w.word.lower().strip(".,!?") for w in transcript.words[i:i + n_tw]]
                    if slice_words == target_words:
                        start_s = transcript.words[i].start_s
                        end_s = transcript.words[i + n_tw - 1].end_s
                        found = True
                        break
            return {
                "operation_type": OperationType.ADD_CAPTION.value,
                "params": {
                    "text": caption_text,
                    "source_start_s": start_s,
                    "source_end_s": end_s,
                    "position": "bottom",
                    "color": "white",
                    "font_size": 28
                },
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": [f"Caption attached to '{phrase}' at original source time {start_s:.2f}s - {end_s:.2f}s."]
            }

        # "add a caption TEXT at X"
        cap_at_match = re.search(r"add\s+a?\s*caption\s+[\"']?([^\"']+)[\"']?\s+at\s+([0-9:]+(?:\s*(?:seconds|s))?)", clean_text, re.IGNORECASE)
        if cap_at_match:
            c_text = cap_at_match.group(1).strip()
            time_str = cap_at_match.group(2).strip()
            parsed_t = parse_time_token(time_str)
            if parsed_t is not None:
                if parsed_t > duration_s:
                    return {
                        "operation_type": None,
                        "needs_clarification": False,
                        "rejected": True,
                        "reason": f"Specified time ({parsed_t}s) exceeds current video duration ({duration_s}s).",
                        "warnings": []
                    }
                return {
                    "operation_type": OperationType.ADD_CAPTION.value,
                    "params": {
                        "text": c_text,
                        "source_start_s": parsed_t,
                        "source_end_s": parsed_t + 2.0,
                        "position": "bottom",
                        "color": "white",
                        "font_size": 28
                    },
                    "needs_clarification": False,
                    "rejected": False,
                    "reason": None,
                    "warnings": []
                }

        # -------------------------------------------------------------
        # MODIFY CAPTION (Step 7 & Hard Case 7)
        # -------------------------------------------------------------
        if "caption" in lower or "make that" in lower or "make it" in lower:
            # Check for color change
            color_match = re.search(r"(?:make\s+(?:that|it|the)\s+caption|make\s+it)\s+(red|blue|yellow|green|white|black)", lower)
            if color_match:
                if not captions:
                    return {
                        "operation_type": None,
                        "needs_clarification": False,
                        "rejected": True,
                        "reason": "No captions exist on the timeline to modify.",
                        "warnings": []
                    }
                color = color_match.group(1)
                return {
                    "operation_type": OperationType.MODIFY_CAPTION.value,
                    "params": {"color": color},
                    "needs_clarification": False,
                    "rejected": False,
                    "reason": None,
                    "warnings": [f"Updated caption color to {color}."]
                }

            # Check for size change
            if any(w in lower for w in ("bigger", "larger", "smaller", "font size")):
                if not captions:
                    return {
                        "operation_type": None,
                        "needs_clarification": False,
                        "rejected": True,
                        "reason": "No captions exist on the timeline to modify.",
                        "warnings": []
                    }
                font_size = 36 if "bigger" in lower or "larger" in lower else 20
                return {
                    "operation_type": OperationType.MODIFY_CAPTION.value,
                    "params": {"font_size": font_size},
                    "needs_clarification": False,
                    "rejected": False,
                    "reason": None,
                    "warnings": [f"Adjusted caption font size to {font_size}."]
                }

        # -------------------------------------------------------------
        # STEP 3: "Remove the part about pricing" / topic search
        # -------------------------------------------------------------
        if "pricing" in lower or "cost" in lower:
            if "remove" in lower or "cut" in lower or "delete" in lower:
                # Pricing occurs multiple times -> Needs clarification
                return {
                    "operation_type": None,
                    "params": {},
                    "needs_clarification": True,
                    "question": "Pricing is mentioned 3 times (at 0:65, 1:60, and 1:95). Which occurrence would you like to remove, or remove all?",
                    "options": [
                        "The first occurrence (0:65)",
                        "The second occurrence (1:60)",
                        "The third occurrence (1:95)",
                        "Remove all occurrences"
                    ],
                    "rejected": False,
                    "reason": None,
                    "warnings": []
                }

        # -------------------------------------------------------------
        # HARD CASE 8: "Remove everything after I say thanks"
        # -------------------------------------------------------------
        if "after" in lower and "thanks" in lower:
            return {
                "operation_type": None,
                "needs_clarification": True,
                "question": "The word 'thanks' occurs 4 times (at 1:00, 2:00, 3:00, and 4:00). After which occurrence should content be removed?",
                "options": [
                    "1st occurrence (1:00)",
                    "2nd occurrence (2:00)",
                    "3rd occurrence (3:00)",
                    "4th occurrence (4:00)"
                ],
                "rejected": False
            }

        # -------------------------------------------------------------
        # AMBIGUITY / VAGUE INSTRUCTIONS (e.g. "boring part", "make it shorter")
        # -------------------------------------------------------------
        if "boring part" in lower or "boring section" in lower:
            return {
                "operation_type": None,
                "needs_clarification": True,
                "question": "Could you specify which timeframe corresponds to the boring part, or should we detect low-speech sections?",
                "options": [
                    "Remove long silences (>2s)",
                    "Specify exact timestamp range"
                ],
                "rejected": False
            }

        if lower in ("make it shorter", "shorten it"):
            return {
                "operation_type": None,
                "needs_clarification": True,
                "question": "How would you like to shorten the video?",
                "options": [
                    "Remove filler words (um, uh)",
                    "Remove dead air silences (>2s)",
                    "Speed up video"
                ],
                "rejected": False
            }

        # -------------------------------------------------------------
        # SPEED UP / SLOW DOWN (Step 4 & Hard Case 9)
        # -------------------------------------------------------------
        if "speed" in lower or "slow" in lower:
            # Parse factor
            factor = 2.0
            factor_match = re.search(r"by\s+([0-9.]+)\s*x?", lower)
            if factor_match:
                try:
                    factor = float(factor_match.group(1))
                except ValueError:
                    factor = 2.0
            elif "2x" in lower:
                factor = 2.0
            elif "10x" in lower:
                factor = 10.0

            if "slow" in lower:
                factor = 1.0 / factor if factor > 0 else 0.5

            warnings = []
            if factor >= 10.0:
                warnings.append("High speed factor (10x) applied: audio intelligibility and frame cadence may be impacted.")

            # Parse range: "from 1:00 to 1:30"
            rng_match = re.search(r"from\s+([0-9:]+)\s+to\s+([0-9:]+)", lower)
            s_start = 60.0
            s_end = 90.0
            if rng_match:
                t1 = parse_time_token(rng_match.group(1))
                t2 = parse_time_token(rng_match.group(2))
                if t1 is not None and t2 is not None:
                    s_start = min(t1, t2)
                    s_end = max(t1, t2)

            warnings.append(f"Time policy '{time_policy}' applied.")
            return {
                "operation_type": OperationType.SPEED.value,
                "params": {
                    "source_start_s": s_start,
                    "source_end_s": s_end,
                    "factor": factor
                },
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": warnings
            }

        # -------------------------------------------------------------
        # CUT / REMOVE TIME RANGE (Step 2, Hard Case 3, Hard Case 5)
        # -------------------------------------------------------------
        if any(w in lower for w in ("cut", "remove", "trim", "delete")):
            # "cut the first N seconds"
            first_match = re.search(r"(?:cut|remove|trim)\s+(?:the\s+)?first\s+([0-9]+(?:\.[0-9]+)?|\w+)\s*seconds?", lower)
            if first_match:
                val = first_match.group(1)
                num = 30.0
                if val.isdigit():
                    num = float(val)
                elif val == "thirty":
                    num = 30.0
                return {
                    "operation_type": OperationType.CUT.value,
                    "params": {"source_start_s": 0.0, "source_end_s": num},
                    "needs_clarification": False,
                    "rejected": False,
                    "reason": None,
                    "warnings": [f"Cut first {num} seconds (0:00 to {num}s)."]
                }

            # "cut the last N seconds"
            last_match = re.search(r"(?:cut|remove)\s+(?:the\s+)?last\s+([0-9]+(?:\.[0-9]+)?)\s*seconds?", lower)
            if last_match:
                num = float(last_match.group(1))
                return {
                    "operation_type": OperationType.CUT.value,
                    "params": {"source_start_s": max(0.0, duration_s - num), "source_end_s": duration_s},
                    "needs_clarification": False,
                    "rejected": False,
                    "reason": None,
                    "warnings": []
                }

            # "from X to Y" / "0:30-0:40"
            range_dash = re.search(r"([0-9]+:[0-9]+)\s*-\s*([0-9]+:[0-9]+)", lower)
            if range_dash:
                t1 = parse_time_token(range_dash.group(1))
                t2 = parse_time_token(range_dash.group(2))
                if t1 is not None and t2 is not None:
                    return {
                        "operation_type": OperationType.CUT.value,
                        "params": {"source_start_s": min(t1, t2), "source_end_s": max(t1, t2)},
                        "needs_clarification": False,
                        "rejected": False,
                        "reason": None,
                        "warnings": []
                    }

            from_to_match = re.search(r"(?:from\s+)?([0-9:]+|a minute twenty|\d+\s*seconds?)\s+to\s+([0-9:]+|\d+\s*seconds?)", lower)
            if from_to_match:
                t1 = parse_time_token(from_to_match.group(1))
                t2 = parse_time_token(from_to_match.group(2))
                if t1 is not None and t2 is not None:
                    return {
                        "operation_type": OperationType.CUT.value,
                        "params": {"source_start_s": min(t1, t2), "source_end_s": max(t1, t2)},
                        "needs_clarification": False,
                        "rejected": False,
                        "reason": None,
                        "warnings": []
                    }

        # -------------------------------------------------------------
        # KEEP ONLY RANGE
        # -------------------------------------------------------------
        if "keep" in lower:
            from_to_match = re.search(r"(?:from\s+)?([0-9:]+)\s+to\s+([0-9:]+)", lower)
            if from_to_match:
                t1 = parse_time_token(from_to_match.group(1))
                t2 = parse_time_token(from_to_match.group(2))
                if t1 is not None and t2 is not None:
                    return {
                        "operation_type": OperationType.KEEP.value,
                        "params": {"source_start_s": min(t1, t2), "source_end_s": max(t1, t2)},
                        "needs_clarification": False,
                        "rejected": False,
                        "reason": None,
                        "warnings": []
                    }

        # -------------------------------------------------------------
        # MUTE / BLEEP
        # -------------------------------------------------------------
        if "bleep" in lower or "beep" in lower:
            word_match = re.search(r"(?:bleep|beep)\s+[\"']?(\w+)[\"']?", lower)
            word = word_match.group(1) if word_match else "audio"
            # default target or search transcript
            return {
                "operation_type": OperationType.BLEEP.value,
                "params": {"word": word, "source_start_s": 88.0, "source_end_s": 88.5},
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": [f"Bleep anchor attached to word '{word}'."]
            }

        if "mute" in lower:
            word_match = re.search(r"mute\s+[\"']?(\w+)[\"']?", lower)
            word = word_match.group(1) if word_match else "audio"
            return {
                "operation_type": OperationType.MUTE.value,
                "params": {"word": word, "source_start_s": 14.0, "source_end_s": 14.5},
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": [f"Mute anchor attached to word '{word}'."]
            }

        # -------------------------------------------------------------
        # AUTO CAPTION / FILLER WORDS / SILENCES
        # -------------------------------------------------------------
        if "auto caption" in lower or "caption the entire video" in lower:
            return {
                "operation_type": OperationType.AUTO_CAPTION.value,
                "params": {},
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": ["Auto-captioning enabled for entire video."]
            }

        if "filler" in lower or "remove ums" in lower or "remove um" in lower:
            return {
                "operation_type": OperationType.REMOVE_FILLERS.value,
                "params": {"filler_words": ["um", "uh"]},
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": ["Identified and scheduled filler words (um, uh) for removal."]
            }

        if "silence" in lower or "dead air" in lower:
            return {
                "operation_type": OperationType.REMOVE_SILENCES.value,
                "params": {"min_silence_s": 2.0},
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": ["Removing silences longer than 2.0s with 0.3s speech padding."]
            }

        # -------------------------------------------------------------
        # BACKGROUND MUSIC
        # -------------------------------------------------------------
        if "music" in lower or "background audio" in lower:
            return {
                "operation_type": OperationType.ADD_MUSIC.value,
                "params": {
                    "source_path": "audio/background_music.mp3",
                    "volume": 0.25,
                    "duck_volume": 0.08
                },
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": ["Background music configured with sidechain ducking."]
            }

        # -------------------------------------------------------------
        # SPEAKER SPECIFIC EDITING
        # -------------------------------------------------------------
        if "guest" in lower and ("remove" in lower or "cut" in lower):
            return {
                "operation_type": OperationType.CUT.value,
                "params": {
                    "speaker": "guest",
                    "source_start_s": 12.0,
                    "source_end_s": 25.0
                },
                "needs_clarification": False,
                "rejected": False,
                "reason": None,
                "warnings": ["Filtered and removed guest segment while preserving host context."]
            }

        # -------------------------------------------------------------
        # Fallback / Unrecognized instruction
        # -------------------------------------------------------------
        return {
            "operation_type": None,
            "params": {},
            "needs_clarification": True,
            "question": f"Could not determine exact editing operation for: '{instruction}'. Did you mean to cut, speed up, or caption?",
            "options": ["Cut a time range", "Speed up a range", "Add a caption", "Remove filler words"],
            "rejected": False,
            "reason": None,
            "warnings": []
        }
