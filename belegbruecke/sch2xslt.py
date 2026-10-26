"""Minimal ISO Schematron (queryBinding xslt2) -> XSLT 3.0 compiler.

Written because the usual compilers (SchXslt, the ISO skeleton) are not reachable
from this sandbox. It supports exactly what the KoSIT XRechnung rules use:
ns, let (schema, pattern and rule level), include, pattern, rule, assert, report,
name, value-of and embedded xsl:function. Output is SVRL-like:
svrl:failed-assert / svrl:successful-report with id, flag and location.
Rule semantics follow Schematron: within one pattern, a node is handled by the
first rule whose context matches it.
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from lxml import etree

SCH = "http://purl.oclc.org/dsdl/schematron"
XSL = "http://www.w3.org/1999/XSL/Transform"
S = f"{{{SCH}}}"


def load(path: Path) -> etree._Element:
    root = etree.parse(str(path)).getroot()
    # resolve sch:include in place
    for inc in list(root.iter(f"{S}include")):
        target = (path.parent / inc.get("href")).resolve()
        inc_root = load(target)
        inc.getparent().replace(inc, inc_root)
    return root


def message(el: etree._Element) -> str:
    out = [escape(el.text or "")]
    for child in el:
        if child.tag == f"{S}name":
            out.append('<xsl:value-of select="name()"/>')
        elif child.tag == f"{S}value-of":
            out.append(f'<xsl:value-of select={quoteattr(child.get("select"))}/>')
        else:
            out.append(escape("".join(child.itertext())))
        out.append(escape(child.tail or ""))
    return " ".join("".join(out).split())


def compile_schema(sch_path: Path) -> str:
    root = load(sch_path)
    ns = {n.get("prefix"): n.get("uri") for n in root.iter(f"{S}ns")}
    for prefix, uri in root.nsmap.items():
        if prefix and uri not in (SCH,):
            ns.setdefault(prefix, uri)
    ns.setdefault("xs", "http://www.w3.org/2001/XMLSchema")
    decls = " ".join(f'xmlns:{p}="{u}"' for p, u in ns.items() if p not in ("xsl", "svrl"))

    parts = [f'<xsl:stylesheet version="3.0" xmlns:xsl="{XSL}" '
             f'xmlns:svrl="http://purl.oclc.org/dsdl/svrl" {decls} exclude-result-prefixes="#all">']

    # embedded xsl:function and friends, copied verbatim
    for el in root.iter(f"{{{XSL}}}function"):
        parts.append(etree.tostring(el, encoding="unicode", with_tail=False))

    # global variables: schema-level and pattern-level lets, in document order
    for let in root.iter(f"{S}let"):
        parent = let.getparent()
        if parent.tag in (f"{S}schema", f"{S}pattern"):
            parts.append(f'<xsl:variable name="{let.get("name")}" select={quoteattr(let.get("value"))}/>')

    patterns = [p for p in root.iter(f"{S}pattern") if p.findall(f"{S}rule")]
    parts.append('<xsl:template match="/"><svrl:schematron-output>')
    for i, _ in enumerate(patterns):
        parts.append(f'<xsl:for-each select="(descendant-or-self::node(), descendant::*/@*)">'
                     f'<xsl:apply-templates select="." mode="p{i}"/></xsl:for-each>')
    parts.append('</svrl:schematron-output></xsl:template>')

    for i, pattern in enumerate(patterns):
        parts.append(f'<xsl:template match="node()|@*" mode="p{i}" priority="-1000"/>')
        rules = pattern.findall(f"{S}rule")
        for j, rule in enumerate(rules):
            prio = 1000 - j
            body = []
            for let in rule.findall(f"{S}let"):
                body.append(f'<xsl:variable name="{let.get("name")}" select={quoteattr(let.get("value"))}/>')
            for test_el in rule:
                if test_el.tag not in (f"{S}assert", f"{S}report"):
                    continue
                is_assert = test_el.tag == f"{S}assert"
                cond = f"not({test_el.get('test')})" if is_assert else test_el.get("test")
                kind = "failed-assert" if is_assert else "successful-report"
                body.append(
                    f'<xsl:if test={quoteattr(cond)}><svrl:{kind} id="{test_el.get("id", "")}" '
                    f'flag="{test_el.get("flag", "fatal")}" location="{{path()}}">'
                    f'<svrl:text>{message(test_el)}</svrl:text></svrl:{kind}></xsl:if>')
            parts.append(f'<xsl:template match={quoteattr(rule.get("context"))} mode="p{i}" priority="{prio}">'
                         + "".join(body) + "</xsl:template>")
    parts.append("</xsl:stylesheet>")
    return "\n".join(parts)


if __name__ == "__main__":
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.write_text(compile_schema(src), encoding="utf-8")
    print(f"compiled {src.name} -> {dst}")
