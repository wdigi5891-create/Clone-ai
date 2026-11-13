"""Exports : JSON / Markdown / SRT, archive ZIP complète et rapport PDF."""
import io
import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from models import Project
from services import prompt_engine
from services.prompt_engine import ts
from services.storage import get_storage

FIELD_LABELS = {
    "location": "Lieu", "set_design": "Décor", "time_of_day": "Moment de la journée",
    "character_positions": "Position des personnages", "actions": "Actions", "gestures": "Gestes",
    "expressions": "Expressions", "movements": "Mouvements", "lighting": "Éclairage", "mood": "Ambiance",
    "camera_type": "Type de caméra", "camera_angle": "Angle de caméra",
    "camera_movement": "Mouvement de caméra", "ambient_sounds": "Sons d'ambiance", "music": "Musique",
}
CHARACTER_LABELS = {
    "physical_description": "Description physique", "skin_tone_appearance": "Teint et apparence",
    "hair": "Coiffure", "clothing": "Vêtements", "accessories": "Accessoires",
    "apparent_age": "Âge apparent estimé", "facial_expressions": "Expressions faciales",
    "posture": "Posture", "distinctive_features": "Particularités distinctives",
}


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def line_text(l) -> str:
    return l.text.strip() if l.identifiable and l.text.strip() else "[Dialogue non identifiable]"


def characters_json(p: Project) -> list[dict]:
    return [{"id": c.label, "scenes": c.scene_indexes, **{CHARACTER_LABELS[k]: v for k, v in (c.data or {}).items() if k in CHARACTER_LABELS},
             "prompt_descriptor": c.prompt_descriptor,
             "reference_image": f"characters/{Path(c.reference_key).name}" if c.reference_key else None}
            for c in p.characters]


def characters_md(p: Project) -> str:
    out = [f"# Fiches personnages — {p.name}", "",
           "_Identifiants neutres et descriptions visuelles : aucune personne réelle n'est identifiée._", ""]
    for c in p.characters:
        out += [f"## {c.label}", f"**Scènes :** {', '.join(map(str, c.scene_indexes or [])) or '—'}", ""]
        out += [f"- **{label} :** {(c.data or {}).get(k) or '—'}" for k, label in CHARACTER_LABELS.items()]
        out += ["", f"**Bloc prompt (réutilisé dans chaque scène) :** {c.prompt_descriptor}", ""]
    return "\n".join(out)


def storyboard_json(p: Project) -> list[dict]:
    return [{"scene": s.index, "start": s.start, "end": s.end, "duration": round(s.end - s.start, 2),
             "characters": s.character_indexes, "analysis": s.data, "description": s.description,
             "frames": [{"file": f"frames/{Path(f.key).name}", "kind": f.kind, "timestamp": f.timestamp,
                         "representative": f.is_representative} for f in s.frames],
             "dialogues": [{"start": l.start, "end": l.end, "character": l.character_index, "text": line_text(l)}
                           for l in prompt_engine.lines_for(p, s)]} for s in p.scenes]


def storyboard_md(p: Project) -> str:
    out = [f"# Storyboard — {p.name}", ""]
    for s in p.scenes:
        out += [f"## SCÈNE {s.index:02d}", f"**Durée :** {ts(s.start)} – {ts(s.end)}", ""]
        rep = next((f for f in s.frames if f.is_representative), None)
        if rep:
            out += [f"![Scène {s.index}](frames/{Path(rep.key).name})", ""]
        out += [f"- **Personnages présents :** {', '.join(f'Personnage {i}' for i in s.character_indexes or []) or '—'}"]
        out += [f"- **{label} :** {(s.data or {}).get(k) or '—'}" for k, label in FIELD_LABELS.items()]
        lines = prompt_engine.lines_for(p, s)
        if lines:
            out += ["- **Dialogues :**"] + [f"  - [{ts(l.start)}] {line_text(l)}" for l in lines]
        out += ["", s.description or "", ""]
    return "\n".join(out)


def dialogues_json(p: Project) -> list[dict]:
    return [{"scene": l.scene_index, "start": l.start, "end": l.end,
             "character": f"Personnage {l.character_index}" if l.character_index else None,
             "text": line_text(l), "identifiable": l.identifiable, "language": l.language,
             "tone": l.tone, "emotion": l.emotion, "intensity": l.intensity, "pace": l.pace,
             "edited": l.edited} for l in p.dialogues]


def dialogues_srt(p: Project) -> str:
    out = []
    for i, l in enumerate(p.dialogues, 1):
        who = f"Personnage {l.character_index} : " if l.character_index else ""
        out.append(f"{i}\n{_srt_time(l.start)} --> {_srt_time(max(l.end, l.start + 0.1))}\n{who}{line_text(l)}\n")
    return "\n".join(out)


def prompts_txt(p: Project) -> str:
    scenes = [s for s in p.scenes if s.prompt_text]
    return (prompt_engine.NOTICE + "\n\n" + ("\n\n" + "=" * 60 + "\n\n").join(s.prompt_text for s in scenes)) if scenes else ""


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def images_zip(p: Project) -> bytes:
    buf = io.BytesIO()
    storage = get_storage()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        for f in p.frames:
            z.writestr(f"frames/{Path(f.key).name}", storage.read(f.key))
        for c in p.characters:
            if c.reference_key:
                z.writestr(f"characters/{Path(c.reference_key).name}", storage.read(c.reference_key))
    return buf.getvalue()


def full_zip(p: Project) -> bytes:
    buf = io.BytesIO()
    storage = get_storage()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in p.frames:
            z.writestr(zipfile.ZipInfo(f"frames/{Path(f.key).name}"), storage.read(f.key), zipfile.ZIP_STORED)
        for c in p.characters:
            if c.reference_key:
                z.writestr(zipfile.ZipInfo(f"characters/{Path(c.reference_key).name}"),
                           storage.read(c.reference_key), zipfile.ZIP_STORED)
        z.writestr("characters/characters.json", _dump(characters_json(p)))
        z.writestr("characters/characters.md", characters_md(p))
        z.writestr("storyboard/storyboard.json", _dump(storyboard_json(p)))
        z.writestr("storyboard.md", storyboard_md(p))
        z.writestr("dialogues/dialogues.json", _dump(dialogues_json(p)))
        z.writestr("dialogues/dialogues.srt", dialogues_srt(p))
        for s in p.scenes:
            if s.prompt_text:
                z.writestr(f"prompts/scene_{s.index:02d}.txt", s.prompt_text)
        z.writestr("prompts/all_scenes.txt", prompts_txt(p))
        z.writestr("prompts/global_prompt.txt", p.global_prompt or prompt_engine.build_global_prompt(p, False))
        z.writestr("script.md", prompt_engine.build_script(p))
        z.writestr("report.pdf", report_pdf(p))
        z.writestr("README.txt", f"AI VIDEO CLONER — export du projet « {p.name} »\n{prompt_engine.NOTICE}\n")
    return buf.getvalue()


def _fonts() -> tuple[str, str]:
    """DejaVu si disponible (Unicode étendu), sinon Helvetica."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    base = Path("/usr/share/fonts/truetype/dejavu")
    try:
        if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont("DejaVu", str(base / "DejaVuSans.ttf")))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(base / "DejaVuSans-Bold.ttf")))
        return "DejaVu", "DejaVu-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold"


def report_pdf(p: Project) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    font, bold = _fonts()
    violet, ink, muted = colors.HexColor("#6d4aff"), colors.HexColor("#14162b"), colors.HexColor("#5b6078")
    st = {
        "title": ParagraphStyle("t", fontName=bold, fontSize=24, leading=30, textColor=ink),
        "h1": ParagraphStyle("h1", fontName=bold, fontSize=15, leading=20, textColor=violet, spaceBefore=10, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName=bold, fontSize=11.5, leading=15, textColor=ink, spaceBefore=8, spaceAfter=3),
        "p": ParagraphStyle("p", fontName=font, fontSize=9.2, leading=13, textColor=ink),
        "small": ParagraphStyle("s", fontName=font, fontSize=8, leading=11, textColor=muted),
        "mono": ParagraphStyle("m", fontName=font, fontSize=8.2, leading=11.5, textColor=ink,
                               backColor=colors.HexColor("#f3f1ff"), borderPadding=6, spaceBefore=4, spaceAfter=8),
    }
    P = lambda text, style="p": Paragraph(escape(str(text or "—")).replace("\n", "<br/>"), st[style])
    storage = get_storage()

    def image(key: str, max_w: float, max_h: float):
        try:
            from reportlab.lib.utils import ImageReader
            data = io.BytesIO(storage.read(key))
            w, h = ImageReader(data).getSize()
            k = min(max_w / w, max_h / h)
            data.seek(0)
            return Image(data, width=w * k, height=h * k)
        except Exception:
            return P("(image indisponible)", "small")

    def table(rows):
        t = Table([[P(a, "small"), P(b)] for a, b in rows], colWidths=[42 * mm, 128 * mm])
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#dcdcec")),
                               ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        return t

    el = [P("AI VIDEO CLONER", "small"), P(p.name, "title"), Spacer(1, 4),
          P("Rapport d'analyse et de reconstruction vidéo", "small"),
          P("Les prompts de ce rapport sont une reconstruction fondée sur l'analyse de l'image et du son "
            "de la vidéo ; ce ne sont pas les prompts d'origine.", "small"),
          Spacer(1, 10), P("Analyse générale", "h1"),
          table([("Durée", f"{p.duration:.1f} s"), ("Résolution", f"{p.width} × {p.height} ({p.orientation})"),
                 ("Fréquence d'images", f"{p.fps:g} i/s"),
                 ("Format", (Path(p.original_filename).suffix.lstrip(".") or p.format.split(",")[0]).upper()),
                 ("Scènes", len(p.scenes)), ("Personnages", len(p.characters)),
                 ("Langue parlée", p.language or "non détectée"), ("Ambiance", p.mood),
                 ("Style visuel", p.visual_style), ("Résumé", p.summary)])]
    if p.characters:
        el += [PageBreak(), P("Personnages", "h1")]
        for c in p.characters:
            rows = [("Scènes", ", ".join(map(str, c.scene_indexes or [])))]
            rows += [(label, (c.data or {}).get(k)) for k, label in CHARACTER_LABELS.items()]
            rows.append(("Bloc prompt", c.prompt_descriptor))
            el.append(P(c.label, "h2"))
            if c.reference_key:
                el += [image(c.reference_key, 45 * mm, 55 * mm), Spacer(1, 4)]
            el += [table(rows), Spacer(1, 8)]
    el += [PageBreak(), P("Storyboard et prompts", "h1")]
    for s in p.scenes:
        el.append(P(f"SCÈNE {s.index:02d} — {ts(s.start)} à {ts(s.end)}", "h2"))
        shots = [image(f.key, 54 * mm, 60 * mm) for f in s.frames[:3]]
        if shots:
            el += [Table([shots], colWidths=[57 * mm] * len(shots)), Spacer(1, 4)]
        rows = [("Personnages", ", ".join(f"Personnage {i}" for i in s.character_indexes or []))]
        rows += [(label, (s.data or {}).get(k)) for k, label in FIELD_LABELS.items()]
        lines = prompt_engine.lines_for(p, s)
        if lines:
            rows.append(("Dialogues", "\n".join(
                f"[{ts(l.start)}] " + (f"Personnage {l.character_index} : " if l.character_index else "") + line_text(l)
                for l in lines)))
        el.append(table(rows))
        if s.description:
            el += [Spacer(1, 4), P(s.description)]
        if s.prompt_text:
            el += [P("Prompt de reconstruction", "small"), P(s.prompt_text, "mono")]
        el.append(Spacer(1, 10))
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=16 * mm, title=f"AI Video Cloner — {p.name}").build(el)
    return buf.getvalue()


EXPORTS = {
    "images.zip": (images_zip, "application/zip"),
    "characters.json": (lambda p: _dump(characters_json(p)), "application/json"),
    "characters.md": (characters_md, "text/markdown"),
    "storyboard.json": (lambda p: _dump(storyboard_json(p)), "application/json"),
    "storyboard.md": (storyboard_md, "text/markdown"),
    "dialogues.json": (lambda p: _dump(dialogues_json(p)), "application/json"),
    "dialogues.srt": (dialogues_srt, "application/x-subrip"),
    "prompts.txt": (prompts_txt, "text/plain"),
    "global_prompt.txt": (lambda p: p.global_prompt or prompt_engine.build_global_prompt(p, False), "text/plain"),
    "script.md": (prompt_engine.build_script, "text/markdown"),
    "report.pdf": (report_pdf, "application/pdf"),
    "all.zip": (full_zip, "application/zip"),
}
