#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageStat, ImageFilter


@dataclass
class LogoJudgeResult:
    passed: bool
    reason: str
    score: float


class LogoJudgeAgent:
    """Heuristic logo quality judge for filtering weak/blank/non-meaningful logo files."""

    def __init__(self, min_w: int = 40, min_h: int = 40):
        self.min_w = min_w
        self.min_h = min_h

    def judge(self, logo_path: str) -> LogoJudgeResult:
        p = Path(logo_path)
        if not p.exists() or p.stat().st_size == 0:
            return LogoJudgeResult(False, "missing_logo_file", 0.0)

        try:
            img = Image.open(p).convert("RGBA")
        except Exception:
            return LogoJudgeResult(False, "invalid_logo_file", 0.0)

        w, h = img.size
        if w < self.min_w or h < self.min_h:
            return LogoJudgeResult(False, "logo_too_small", 0.1)

        # Ignore transparent pixels when checking whiteness.
        rgba = img.getdata()
        non_transparent = [(r, g, b) for (r, g, b, a) in rgba if a > 16]
        if len(non_transparent) < max(100, int(w * h * 0.02)):
            return LogoJudgeResult(False, "logo_too_transparent_or_empty", 0.1)

        white_like = 0
        for r, g, b in non_transparent:
            if r > 245 and g > 245 and b > 245:
                white_like += 1
        white_ratio = white_like / max(len(non_transparent), 1)
        if white_ratio > 0.95:
            return LogoJudgeResult(False, "logo_mostly_white", 0.15)

        # Low variance often means plain block / non-informative image.
        rgb = Image.new("RGB", img.size)
        rgb.putdata([(r, g, b) for (r, g, b, a) in img.getdata()])
        stat = ImageStat.Stat(rgb)
        var_mean = sum(stat.var) / 3.0
        if var_mean < 35:
            return LogoJudgeResult(False, "logo_low_variance", 0.2)

        # Edge density: too few edges => likely blank/simple background.
        edges = rgb.convert("L").filter(ImageFilter.FIND_EDGES)
        e_stat = ImageStat.Stat(edges)
        edge_strength = e_stat.mean[0]
        if edge_strength < 8:
            return LogoJudgeResult(False, "logo_low_edge_density", 0.25)

        # Combined score (simple weighted heuristic)
        score = min(1.0, 0.35 * (1 - white_ratio) + 0.35 * min(var_mean / 200, 1.0) + 0.30 * min(edge_strength / 60, 1.0))
        if score < 0.45:
            return LogoJudgeResult(False, "logo_not_meaningful", score)

        return LogoJudgeResult(True, "ok", score)
