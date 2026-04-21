from __future__ import annotations

import csv
import io
import json
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from cielab_gamut_tools.cli._resolve import NAMED_GAMUTS, display_name, resolve_gamut

app = typer.Typer(
    help="Calculate gamut metrics (volume, coverage, comparison).",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True)


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    csv = "csv"


class Standard(str, Enum):
    IDMS = "IDMS"
    IEC_62977 = "IEC-62977"
    IEC_62906 = "IEC-62906"


_STANDARD_NAMES: dict[Standard, str] = {
    Standard.IDMS: "ICDM Information Display Measurements Standard v1.3, \u00a75.32",
    Standard.IEC_62977: "IEC 62977-3-5 \u2014 Electronic displays: Colour capabilities",
    Standard.IEC_62906: "IEC 62906-6-1 \u2014 Displays: Colour gamut intersection visualisation",
}


def _emit(out_text: str, output: Optional[Path], quiet: bool) -> None:
    if output:
        output.write_text(out_text, encoding="utf-8")
        if not quiet:
            console.print(f"Results written to {output}")
    else:
        sys.stdout.write(out_text)


@app.command()
def volume(
    files: Annotated[
        list[str],
        typer.Argument(
            help=(
                "CGATS file(s) or named gamut(s). "
                f"Named: {', '.join(NAMED_GAMUTS)}."
            )
        ),
    ],
    format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format."),
    ] = OutputFormat.text,
    standard: Annotated[
        Optional[Standard],
        typer.Option("--standard", help="Append standards traceability metadata."),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Write results to file."),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Values only — no labels."),
    ] = False,
) -> None:
    """Calculate gamut volume for one or more CGATS files or named gamuts."""
    results = []
    for arg in files:
        gamut = resolve_gamut(arg)
        vol = gamut.volume()
        results.append({"file": arg, "volume": vol})

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    out_text: str
    if format == OutputFormat.json:
        records = []
        for r in results:
            rec: dict = {
                "file": r["file"],
                "volume": round(r["volume"], 1),
                "unit": "deltaE_ab_cubed",
            }
            if standard is not None:
                rec["standard"] = _STANDARD_NAMES[standard]
                rec["method"] = "cylindrical_integration"
                rec["calculated"] = timestamp
            records.append(rec)
        payload = records[0] if len(records) == 1 else records
        out_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    elif format == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["file", "volume_dEab3"], lineterminator="\n")
        writer.writeheader()
        for r in results:
            writer.writerow({"file": r["file"], "volume_dEab3": round(r["volume"], 1)})
        out_text = buf.getvalue()

    else:  # text
        if quiet:
            out_text = "\n".join(f"{r['volume']:.0f}" for r in results) + "\n"
        elif len(results) == 1:
            r = results[0]
            out_text = f"Volume: {r['volume']:,.0f} (\u0394E*ab)\u00b3\n"
            if standard is not None:
                out_text += f"Standard: {_STANDARD_NAMES[standard]}\n"
        else:
            tab = Table(show_header=True, header_style="bold")
            tab.add_column("File")
            tab.add_column("Volume (\u0394E*ab)\u00b3", justify="right")
            for r in results:
                tab.add_row(r["file"], f"{r['volume']:,.0f}")
            if output:
                header = f"{'File':<40}  {'Volume (ΔE*ab)³':>18}"
                rows = [f"{r['file']:<40}  {r['volume']:>18,.0f}" for r in results]
                out_text = "\n".join([header, "-" * len(header)] + rows) + "\n"
                _emit(out_text, output, quiet)
            else:
                console.print(tab)
            return

    _emit(out_text, output, quiet)


@app.command()
def coverage(
    dut: Annotated[
        str,
        typer.Argument(
            help=(
                "DUT CGATS file or named gamut. "
                f"Named: {', '.join(NAMED_GAMUTS)}."
            )
        ),
    ],
    reference: Annotated[
        str,
        typer.Option(
            "--reference",
            "-r",
            help=(
                "Reference gamut(s) — comma-separated named gamuts or file paths. "
                f"Named: {', '.join(NAMED_GAMUTS)}."
            ),
        ),
    ],
    format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format."),
    ] = OutputFormat.text,
    standard: Annotated[
        Optional[Standard],
        typer.Option("--standard", help="Append standards traceability metadata."),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Write results to file."),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Values only — no labels."),
    ] = False,
) -> None:
    """Calculate DUT coverage of one or more reference gamuts."""
    dut_gamut = resolve_gamut(dut)
    dut_vol = dut_gamut.volume()
    dut_label = display_name(dut)

    ref_args = [r.strip() for r in reference.split(",")]
    results = []
    for ref_arg in ref_args:
        ref_gamut = resolve_gamut(ref_arg)
        ref_vol = ref_gamut.volume()
        int_vol = dut_gamut.intersect(ref_gamut).volume()
        results.append(
            {
                "reference": ref_arg,
                "ref_label": display_name(ref_arg),
                "coverage_pct": int_vol / ref_vol * 100,
                "dut_volume": dut_vol,
                "ref_volume": ref_vol,
                "intersection_volume": int_vol,
            }
        )

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    out_text: str
    if format == OutputFormat.json:
        records = []
        for r in results:
            rec: dict = {
                "dut": dut,
                "reference": r["reference"],
                "coverage_pct": round(r["coverage_pct"], 1),
                "dut_volume": round(r["dut_volume"], 1),
                "ref_volume": round(r["ref_volume"], 1),
                "intersection_volume": round(r["intersection_volume"], 1),
                "unit": "deltaE_ab_cubed",
            }
            if standard is not None:
                rec["standard"] = _STANDARD_NAMES[standard]
                rec["method"] = "cylindrical_integration"
                rec["calculated"] = timestamp
            records.append(rec)
        payload = records[0] if len(records) == 1 else records
        out_text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"

    elif format == OutputFormat.csv:
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=[
                "reference", "coverage_pct",
                "dut_volume_dEab3", "ref_volume_dEab3", "intersection_volume_dEab3",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "reference": r["reference"],
                    "coverage_pct": round(r["coverage_pct"], 1),
                    "dut_volume_dEab3": round(r["dut_volume"], 1),
                    "ref_volume_dEab3": round(r["ref_volume"], 1),
                    "intersection_volume_dEab3": round(r["intersection_volume"], 1),
                }
            )
        out_text = buf.getvalue()

    else:  # text
        if quiet:
            out_text = "\n".join(f"{r['coverage_pct']:.1f}" for r in results) + "\n"
            _emit(out_text, output, quiet)
            return
        if len(results) == 1:
            r = results[0]
            w = 24
            out_text = (
                f"{r['ref_label']} coverage:  {r['coverage_pct']:>6.1f}%\n"
                f"{'  ' + dut_label + ' volume:':<{w}} {r['dut_volume']:>12,.0f} (\u0394E*ab)\u00b3\n"
                f"{'  ' + r['ref_label'] + ' volume:':<{w}} {r['ref_volume']:>12,.0f} (\u0394E*ab)\u00b3\n"
                f"{'  Intersection:':<{w}} {r['intersection_volume']:>12,.0f} (\u0394E*ab)\u00b3\n"
            )
            if standard is not None:
                out_text += f"Standard: {_STANDARD_NAMES[standard]}\n"
            _emit(out_text, output, quiet)
        else:
            tab = Table(show_header=True, header_style="bold", title=f"{dut_label} coverage")
            tab.add_column("Reference")
            tab.add_column("Coverage", justify="right")
            tab.add_column("DUT vol (\u0394E*ab)\u00b3", justify="right")
            tab.add_column("Ref vol (\u0394E*ab)\u00b3", justify="right")
            tab.add_column("Intersection", justify="right")
            for r in results:
                tab.add_row(
                    r["ref_label"],
                    f"{r['coverage_pct']:.1f}%",
                    f"{r['dut_volume']:,.0f}",
                    f"{r['ref_volume']:,.0f}",
                    f"{r['intersection_volume']:,.0f}",
                )
            if output:
                lines = [
                    f"{'Reference':<16}  {'Coverage':>10}  {'DUT vol':>12}  "
                    f"{'Ref vol':>12}  {'Intersection':>12}",
                    "-" * 70,
                ]
                for r in results:
                    lines.append(
                        f"{r['ref_label']:<16}  {r['coverage_pct']:>9.1f}%"
                        f"  {r['dut_volume']:>12,.0f}  {r['ref_volume']:>12,.0f}"
                        f"  {r['intersection_volume']:>12,.0f}"
                    )
                _emit("\n".join(lines) + "\n", output, quiet)
            else:
                console.print(tab)
        return

    _emit(out_text, output, quiet)


@app.command()
def compare(
    gamuts: Annotated[
        list[str],
        typer.Argument(
            help=(
                "Two or more CGATS files or named gamuts to compare. "
                f"Named: {', '.join(NAMED_GAMUTS)}."
            )
        ),
    ],
    reference: Annotated[
        Optional[str],
        typer.Option(
            "--reference",
            "-r",
            help=(
                "Compare each gamut's coverage of this reference (named or file). "
                "Mutually exclusive with --matrix."
            ),
        ),
    ] = None,
    matrix: Annotated[
        bool,
        typer.Option(
            "--matrix",
            help="Show full pairwise intersection matrix. Mutually exclusive with --reference.",
        ),
    ] = False,
    format: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", help="Output format."),
    ] = OutputFormat.text,
    standard: Annotated[
        Optional[Standard],
        typer.Option("--standard", help="Append standards traceability metadata."),
    ] = None,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Write results to file."),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Values only — no labels."),
    ] = False,
) -> None:
    """Compare volumes, coverage, or pairwise intersections across multiple gamuts."""
    if reference and matrix:
        err_console.print("[red]--reference and --matrix are mutually exclusive.[/red]")
        raise typer.Exit(1)
    if len(gamuts) < 2:
        err_console.print("[red]compare requires at least two gamuts.[/red]")
        raise typer.Exit(1)

    loaded = [(arg, display_name(arg), resolve_gamut(arg)) for arg in gamuts]
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    std_meta = (
        {"standard": _STANDARD_NAMES[standard], "calculated": timestamp}
        if standard is not None
        else {}
    )

    # ------------------------------------------------------------------ MATRIX
    if matrix:
        n = len(loaded)
        labels = [lbl for _, lbl, _ in loaded]
        vols = [g.volume() for _, _, g in loaded]

        # Compute unique intersections (upper triangle) and reuse by symmetry
        int_vols: dict[tuple[int, int], float] = {}
        for i in range(n):
            for j in range(i + 1, n):
                iv = loaded[i][2].intersect(loaded[j][2]).volume()
                int_vols[(i, j)] = iv
                int_vols[(j, i)] = iv

        def pct(i: int, j: int) -> float:
            return 100.0 if i == j else int_vols[(i, j)] / vols[j] * 100

        if format == OutputFormat.json:
            payload: dict = {
                "labels": labels,
                "matrix_pct": [[round(pct(i, j), 1) for j in range(n)] for i in range(n)],
                "description": "% of column gamut covered by row gamut",
                **std_meta,
            }
            _emit(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", output, quiet)

        elif format == OutputFormat.csv:
            buf = io.StringIO()
            w = csv.writer(buf, lineterminator="\n")
            w.writerow([""] + labels)
            for i in range(n):
                w.writerow([labels[i]] + [f"{pct(i, j):.1f}" for j in range(n)])
            _emit(buf.getvalue(), output, quiet)

        else:  # text
            tab = Table(
                title="Pairwise Intersections (% of column gamut covered by row)",
                header_style="bold",
            )
            tab.add_column("")
            for lbl in labels:
                tab.add_column(lbl, justify="right")
            for i in range(n):
                tab.add_row(labels[i], *[f"{pct(i, j):.0f}%" for j in range(n)])
            if output:
                col_w = max(len(l) for l in labels) + 2
                rows = [" " * col_w + "".join(f"{l:>{col_w}}" for l in labels)]
                for i in range(n):
                    rows.append(
                        f"{labels[i]:>{col_w}}"
                        + "".join(f"{pct(i, j):>{col_w - 1}.0f}%" for j in range(n))
                    )
                _emit("\n".join(rows) + "\n", output, quiet)
            else:
                console.print(tab)
        return

    # --------------------------------------------------------------- COVERAGE
    if reference is not None:
        ref_gamut = resolve_gamut(reference)
        ref_vol = ref_gamut.volume()
        ref_label = display_name(reference)

        cov_results = [
            {
                "gamut": arg,
                "label": lbl,
                "coverage_pct": (iv := g.intersect(ref_gamut).volume()) / ref_vol * 100,
                "intersection_volume": iv,
            }
            for arg, lbl, g in loaded
        ]

        if format == OutputFormat.json:
            records = [
                {
                    "gamut": r["gamut"],
                    "reference": reference,
                    "coverage_pct": round(r["coverage_pct"], 1),
                    "intersection_volume": round(r["intersection_volume"], 1),
                    "ref_volume": round(ref_vol, 1),
                    "unit": "deltaE_ab_cubed",
                    **std_meta,
                }
                for r in cov_results
            ]
            _emit(json.dumps(records, indent=2, ensure_ascii=False) + "\n", output, quiet)

        elif format == OutputFormat.csv:
            buf = io.StringIO()
            w2 = csv.DictWriter(
                buf,
                fieldnames=["gamut", "coverage_pct", "intersection_volume_dEab3"],
                lineterminator="\n",
            )
            w2.writeheader()
            for r in cov_results:
                w2.writerow(
                    {
                        "gamut": r["gamut"],
                        "coverage_pct": round(r["coverage_pct"], 1),
                        "intersection_volume_dEab3": round(r["intersection_volume"], 1),
                    }
                )
            _emit(buf.getvalue(), output, quiet)

        else:  # text
            if quiet:
                _emit(
                    "\n".join(f"{r['coverage_pct']:.1f}" for r in cov_results) + "\n",
                    output, quiet,
                )
                return
            tab = Table(title=f"{ref_label} Coverage Comparison", header_style="bold")
            tab.add_column("Gamut")
            tab.add_column("Coverage", justify="right")
            tab.add_column("Intersection (\u0394E*ab)\u00b3", justify="right")
            for r in cov_results:
                tab.add_row(r["label"], f"{r['coverage_pct']:.1f}%", f"{r['intersection_volume']:,.0f}")
            if output:
                lines = [f"{'Gamut':<20}  {'Coverage':>10}  {'Intersection':>14}", "-" * 48]
                for r in cov_results:
                    lines.append(
                        f"{r['label']:<20}  {r['coverage_pct']:>9.1f}%"
                        f"  {r['intersection_volume']:>14,.0f}"
                    )
                _emit("\n".join(lines) + "\n", output, quiet)
            else:
                console.print(tab)
        return

    # --------------------------------------------------------------- VOLUMES
    vols = [(arg, lbl, g.volume()) for arg, lbl, g in loaded]
    base_vol = vols[0][2]

    if format == OutputFormat.json:
        records2 = [
            {
                "gamut": arg,
                "volume": round(vol, 1),
                "delta_pct_vs_first": round((vol - base_vol) / base_vol * 100, 1),
                "unit": "deltaE_ab_cubed",
                **std_meta,
            }
            for arg, lbl, vol in vols
        ]
        _emit(json.dumps(records2, indent=2, ensure_ascii=False) + "\n", output, quiet)

    elif format == OutputFormat.csv:
        buf = io.StringIO()
        w3 = csv.DictWriter(
            buf,
            fieldnames=["gamut", "volume_dEab3", "delta_pct_vs_first"],
            lineterminator="\n",
        )
        w3.writeheader()
        for arg, lbl, vol in vols:
            w3.writerow(
                {
                    "gamut": arg,
                    "volume_dEab3": round(vol, 1),
                    "delta_pct_vs_first": round((vol - base_vol) / base_vol * 100, 1),
                }
            )
        _emit(buf.getvalue(), output, quiet)

    else:  # text
        if quiet:
            _emit("\n".join(f"{vol:.0f}" for _, _, vol in vols) + "\n", output, quiet)
            return
        tab = Table(title="Gamut Comparison", header_style="bold")
        tab.add_column("Gamut")
        tab.add_column("Volume (\u0394E*ab)\u00b3", justify="right")
        tab.add_column("vs first", justify="right")
        for i, (arg, lbl, vol) in enumerate(vols):
            delta = (vol - base_vol) / base_vol * 100
            tab.add_row(lbl, f"{vol:,.0f}", "\u2014" if i == 0 else f"{delta:+.1f}%")
        if output:
            lines = [f"{'Gamut':<20}  {'Volume':>14}  {'vs first':>10}", "-" * 48]
            for i, (arg, lbl, vol) in enumerate(vols):
                delta_str = "" if i == 0 else f"({(vol - base_vol) / base_vol * 100:+.1f}%)"
                lines.append(f"{lbl:<20}  {vol:>14,.0f}  {delta_str:>10}")
            _emit("\n".join(lines) + "\n", output, quiet)
        else:
            console.print(tab)
