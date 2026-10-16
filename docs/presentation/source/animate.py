"""Adds click-to-reveal (fade in) to shapes named a<N>_...: all shapes with the same N appear on click N.
Usage: python3 animate.py deck.pptx"""
import re, sys, zipfile, shutil, os
from lxml import etree

NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
P = "{%s}" % NS["p"]


def timing(steps, text_ids):
    ids = iter(range(3, 100000))
    clicks = []
    for step in sorted(steps):
        effects = []
        for i, spid in enumerate(steps[step]):
            node = "clickEffect" if i == 0 else "withEffect"
            grp = ' grpId="0"' if spid in text_ids else ""
            c_eff, c_set, c_anim = next(ids), next(ids), next(ids)
            effects.append(
                f'<p:par><p:cTn id="{c_eff}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold"{grp} nodeType="{node}">'
                f'<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                f'<p:set><p:cBhvr><p:cTn id="{c_set}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
                f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
                f'<p:to><p:strVal val="visible"/></p:to></p:set>'
                f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{c_anim}" dur="400"/><p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
                f'</p:childTnLst></p:cTn></p:par>')
        outer, inner = next(ids), next(ids)
        clicks.append(f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
                      f'<p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
                      + "".join(effects) + '</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>')
    bld = "".join(f'<p:bldP spid="{spid}" grpId="0"/>' for step in sorted(steps) for spid in steps[step] if spid in text_ids)
    return (f'<p:timing xmlns:p="{NS["p"]}"><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            f'<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>' + "".join(clicks) +
            '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
            '</p:childTnLst></p:cTn></p:par></p:tnLst>' + (f"<p:bldLst>{bld}</p:bldLst>" if bld else "") + '</p:timing>')


def main(path):
    tmp = path + ".tmp"
    total = 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if re.match(r"ppt/slides/slide\d+\.xml$", item.filename):
                root = etree.fromstring(data)
                steps, text_ids = {}, set()
                for c in root.iter(P + "cNvPr"):
                    m = re.match(r"a(\d+)_", c.get("name", ""))
                    if not m:
                        continue
                    spid = c.get("id")
                    steps.setdefault(int(m.group(1)), []).append(spid)
                    shape = c.getparent().getparent()
                    if shape.tag == P + "sp" and shape.find(P + "txBody") is not None:
                        text_ids.add(spid)
                if steps and root.find(P + "timing") is None:
                    t = etree.fromstring(timing(steps, text_ids))
                    ext = root.find(P + "extLst")
                    if ext is not None:
                        ext.addprevious(t)
                    else:
                        root.append(t)
                    data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
                    total += len(steps)
                    print(f"{item.filename}: {len(steps)} click(s), {sum(len(v) for v in steps.values())} shapes")
            zout.writestr(item, data)
    shutil.move(tmp, path)
    print("clicks added:", total)


if __name__ == "__main__":
    main(sys.argv[1])
