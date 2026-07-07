import fitz, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
doc = fitz.open(r'd:\EBACKUP\New Projects\Resume Parser\HAIRAT - Salesforce BA - Copy.pdf')

# Page dimensions + margins
page = doc[0]
print("PAGE RECT:", page.rect)
print()

# Drawing objects (lines, rectangles)
print("=== DRAWINGS (lines/borders) ===")
paths = page.get_drawings()
for p in paths[:10]:
    print("  rect:", p.get('rect'), "color:", p.get('color'), "fill:", p.get('fill'), "width:", p.get('width'))

print()
print("=== FULL FIRST PAGE SPANS ===")
blocks = page.get_text('dict')['blocks']
for b in blocks[:5]:
    if b.get('type') != 0: continue
    for line in b.get('lines', []):
        for span in line.get('spans', []):
            print(f"  FONT={span['font']} SIZE={round(span['size'],1)} FLAGS={span['flags']} BBOX={[round(x,1) for x in span['bbox']]} TEXT={repr(span['text'][:50])}")
        print()
