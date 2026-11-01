"""Экспортирует правила и базу знаний в web/data.js для статического демо (GitHub Pages).
Один источник правды: kompas/data/*.yaml. Запускать после любой правки базы."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
rules = yaml.safe_load((ROOT / "kompas/data/rules.yaml").read_text(encoding="utf-8"))
kb = yaml.safe_load((ROOT / "kompas/data/kb.yaml").read_text(encoding="utf-8"))
out = ROOT / "web/data.js"
out.write_text("window.KOMPAS_DATA = " + json.dumps({"rules": rules, "kb": kb}, ensure_ascii=False, default=str) + ";\n",
               encoding="utf-8")
print(f"wrote {out.relative_to(ROOT)}")
