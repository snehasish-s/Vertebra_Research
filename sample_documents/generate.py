"""Regenerate three small, original CC0 fixtures; no external dataset is needed."""
import json
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas

DIRECTORY = Path(__file__).parent


def generate():
    corpus = json.loads((DIRECTORY / 'corpus.json').read_text(encoding='utf-8'))
    for document in corpus:
        pdf = canvas.Canvas(str(DIRECTORY / document['filename']), pagesize=(595, 842))
        pdf.setTitle(document['title'])
        for number, page in enumerate(document['pages'], 1):
            pdf.setFillColor(colors.HexColor('#f6f5ef'))
            pdf.rect(0, 0, 595, 842, fill=1, stroke=0)
            pdf.setFillColor(colors.HexColor('#314c39'))
            pdf.setFont('Helvetica-Bold', 10)
            pdf.drawString(54, 779, 'VERTEBRA RESEARCH  /  SAMPLE LIBRARY')
            pdf.setFont('Helvetica', 10)
            pdf.drawString(54, 752, document['title'])
            heading = Paragraph(page['heading'], ParagraphStyle('Heading', fontName='Times-Roman', fontSize=30, leading=35, textColor=colors.HexColor('#314c39')))
            _, height = heading.wrap(487, 130)
            heading.drawOn(pdf, 54, 683 - height)
            paragraph = Paragraph(page['text'], ParagraphStyle('Body', fontName='Helvetica', fontSize=13, leading=23, textColor=colors.HexColor('#52624c')))
            _, height = paragraph.wrap(475, 400)
            paragraph.drawOn(pdf, 54, 563 - height)
            pdf.setStrokeColor(colors.HexColor('#cdd5c1'))
            pdf.line(54, 105, 541, 105)
            pdf.setFont('Helvetica', 9)
            pdf.drawString(54, 83, 'Fictional teaching material | CC0 | Not empirical research')
            pdf.drawRightString(541, 83, f'{number} / {len(document["pages"])}')
            pdf.showPage()
        pdf.save()
        print(document['filename'])


if __name__ == '__main__':
    generate()
