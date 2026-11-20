"""Inject native PowerPoint click animations into a deck built by build_deck.js.

Every shape whose name starts with "a<N>_" fades in on click N of its slide; shapes
sharing N appear together. Also adds a fade transition between slides. Works in
PowerPoint (Mac/Windows) and Keynote.

    python add_animations.py base.pptx ../Fraud_Guard_talk.pptx
"""
import re
import sys
import zipfile
from collections import defaultdict

SRC, DST = sys.argv[1], sys.argv[2]


def effect(ids, spid, node_type, dur=400):
    a, b, c = ids
    return (
        f'<p:par><p:cTn id="{a}" presetID="10" presetClass="entr" presetSubtype="0" fill="hold" grpId="0" nodeType="{node_type}">'
        f'<p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
        f'<p:set><p:cBhvr><p:cTn id="{b}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl><p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst>'
        f'</p:cBhvr><p:to><p:strVal val="visible"/></p:to></p:set>'
        f'<p:animEffect transition="in" filter="fade"><p:cBhvr><p:cTn id="{c}" dur="{dur}"/>'
        f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl></p:cBhvr></p:animEffect>'
        f'</p:childTnLst></p:cTn></p:par>'
    )


def timing_xml(groups, kinds):
    counter = iter(range(3, 100000))
    clicks = []
    for step in sorted(groups):
        outer, inner = next(counter), next(counter)
        effects = "".join(
            effect((next(counter), next(counter), next(counter)), spid, "clickEffect" if i == 0 else "withEffect")
            for i, spid in enumerate(groups[step])
        )
        clicks.append(
            f'<p:par><p:cTn id="{outer}" fill="hold"><p:stCondLst><p:cond delay="indefinite"/></p:stCondLst><p:childTnLst>'
            f'<p:par><p:cTn id="{inner}" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            f'{effects}</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>'
        )
    builds = "".join(
        f'<p:bldP spid="{spid}" grpId="0" animBg="1"/>'
        for step in sorted(groups) for spid in groups[step] if kinds[spid] == "sp"
    )
    return (
        '<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
        '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
        + "".join(clicks)
        + '</p:childTnLst></p:cTn><p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
        '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst></p:seq>'
        '</p:childTnLst></p:cTn></p:par></p:tnLst>'
        + (f"<p:bldLst>{builds}</p:bldLst>" if builds else "")
        + "</p:timing>"
    )


FADE_TRANSITION = '<p:transition spd="med"><p:fade/></p:transition>'

with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        if item.is_dir():  # folder entries break some cloud viewers
            continue
        data = zin.read(item.filename)
        if re.fullmatch(r"ppt/slides/slide\d+\.xml", item.filename):
            xml = data.decode("utf-8")
            groups, kinds = defaultdict(list), {}
            for element in re.finditer(r"<p:(sp|cxnSp)>(.*?)</p:\1>", xml, re.S):
                m = re.search(r'<p:cNvPr id="(\d+)" name="a(\d+)_', element.group(2))
                if m:
                    groups[int(m.group(2))].append(m.group(1))
                    kinds[m.group(1)] = element.group(1)
            assert "<p:timing>" not in xml and "<p:transition" not in xml, item.filename
            insert = FADE_TRANSITION + (timing_xml(groups, kinds) if groups else "")
            # p:transition and p:timing go right after p:clrMapOvr (before any p:extLst).
            xml = re.sub(r"(</p:clrMapOvr>|<p:clrMapOvr/>)", lambda m: m.group(1) + insert, xml, count=1)
            assert insert in xml, f"no clrMapOvr in {item.filename}"
            print(f"{item.filename}: {len(groups)} clicks, {sum(map(len, groups.values()))} shapes")
            data = xml.encode("utf-8")
        zout.writestr(item, data)
