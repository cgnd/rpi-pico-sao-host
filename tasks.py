# SPDX-FileCopyrightText: Common Ground Electronics <https://cgnd.dev>
#
# SPDX-License-Identifier: MIT OR Apache-2.0

import platform
import shutil
import sys
from pathlib import Path

import fitz
import fitz.utils
from invoke.exceptions import UnexpectedExit
from invoke.tasks import task
from reportlab.graphics import renderPDF
from svglib import svglib

if sys.version_info >= (3, 11):
    import inspect

    if not hasattr(inspect, "getargspec"):
        inspect.getargspec = inspect.getfullargspec


def get_kicad_cli_path():
    """Determine the KiCad CLI path based on the operating system."""
    if platform.system() == "Darwin":  # macOS
        # Check for KiCad 9.0 path first
        kicad_9_path = Path(
            "/Applications/KiCad_9.0/KiCad.app/Contents/MacOS/kicad-cli"
        )
        if kicad_9_path.exists():
            return str(kicad_9_path)

        # Fallback to the default KiCad path
        kicad_default_path = Path(
            "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
        )
        if kicad_default_path.exists():
            return str(kicad_default_path)

        # If neither path exists, raise an error
        raise FileNotFoundError("kicad-cli not found")

    # Default for Windows and Linux
    return "kicad-cli"


KICAD_CLI = get_kicad_cli_path()

# Project metadata
ORGANIZATION = "Common Ground Electronics"
ORGANIZATION_URL = "https://cgnd.dev"
COPYRIGHT_HOLDER = ORGANIZATION
COPYRIGHT_HOLDER_CONTACT = ORGANIZATION_URL
SPDX_LICENSE_ID = "CERN-OHL-P-2.0"
PROJECT_NAME = "RPi_Pico_SAO_Host"
PROJECT_DESCRIPTION = "Raspberry Pi Pico SAO Host"
PROJECT_VERSION_MAJOR = "2"
PCB_PART_NUMBER = "100092"
PCB_REV = "A"
SCH_PART_NUMBER = "100093"
SCH_REV = "A"
PCA_PART_NUMBER = "100094"
PCA_REV = "A"

# Input Paths
SCH_PATH = Path(f"{PROJECT_NAME}.kicad_sch")
PCB_PATH = Path(f"{PROJECT_NAME}.kicad_pcb")

# Project Output Path
OUTPUT_PATH = Path(f"output/{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}")

# Report Output Paths
REPORT_OUTPUT_PATH = OUTPUT_PATH / Path("Reports")
ERC_REPORT_PATH = REPORT_OUTPUT_PATH / Path(
    f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_ERC_report.txt"
)
DRC_REPORT_PATH = REPORT_OUTPUT_PATH / Path(
    f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_DRC_report.txt"
)

# PCA Output Paths
PCA_OUTPUT_PATH = OUTPUT_PATH / Path(
    f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_PCA_{PCA_PART_NUMBER}_Rev_{PCA_REV}"
)
SCH_OUTPUT_PATH = PCA_OUTPUT_PATH / Path("Schematic")
BOM_OUTPUT_PATH = PCA_OUTPUT_PATH / Path("BOM")
SCH_PDF_PATH = SCH_OUTPUT_PATH / Path(
    f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_Schematic_{SCH_PART_NUMBER}_Rev_{SCH_REV}.pdf"
)
SCH_SVG_PATH = SCH_OUTPUT_PATH / Path(
    f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_Schematic_{SCH_PART_NUMBER}_Rev_{SCH_REV}_SVG"
)
SCH_PNG_PATH = SCH_OUTPUT_PATH / Path(
    f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_Schematic_{SCH_PART_NUMBER}_Rev_{SCH_REV}.png"
)
BOM_PATH = BOM_OUTPUT_PATH / Path(
    f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_ECAD_BOM_{PCA_PART_NUMBER}_Rev_{PCA_REV}.csv"
)
PCA_RENDER_PATH = PCA_OUTPUT_PATH / Path("Renders")

# PCB Output Paths
PCB_OUTPUT_PATH = OUTPUT_PATH / Path(
    f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_PCB_{PCB_PART_NUMBER}_Rev_{PCB_REV}"
)
GERBERS_PATH = PCB_OUTPUT_PATH / Path("Gerbers")
ODB_PATH = PCB_OUTPUT_PATH / Path("ODB++") / Path(f"{PROJECT_NAME}.zip")
PCB_PDF_PATH = PCB_OUTPUT_PATH / Path("PDF")
DRILL_FILES_PATH = PCB_OUTPUT_PATH / Path("Drill_Files")
IPCD356_PATH = PCB_OUTPUT_PATH / Path("Netlist") / Path(f"{PROJECT_NAME}.d356")
POSITION_PATH = PCB_OUTPUT_PATH / Path("Position") / Path(f"{PROJECT_NAME}.pos")
PCB_RENDER_PATH = OUTPUT_PATH / Path("Renders")


def rm(
    path: str | Path,
    *,
    recursive: bool = False,
    force: bool = False,
    use_glob: bool = False,
) -> None:
    """
    Remove files or directories like the Unix `rm` command.

    Args:
        path: A path or glob pattern to remove.
        recursive: If True, allows recursive deletion of directories.
        force: If True, suppresses errors for non-existent paths.
        use_glob: If True, treats the path as a glob pattern.
    """
    path = Path(path)

    paths = path.parent.glob(path.name) if use_glob else [path]

    for p in paths:
        try:
            if p.is_symlink() or p.is_file():
                p.unlink(missing_ok=force)
            elif p.is_dir():
                if recursive:
                    shutil.rmtree(p, ignore_errors=force)
                else:
                    raise IsADirectoryError(
                        f"Cannot remove directory '{p}' without recursive=True"
                    )
            else:
                if not force:
                    raise OSError(f"Unknown file type: '{p}'")
        except FileNotFoundError:
            if not force:
                raise
        except Exception as e:
            if not force:
                raise e


def ensure_dir(path):
    """Ensure the directory exists for a given path."""
    if isinstance(path, str):
        path = Path(path)
    path.parent.resolve().mkdir(parents=True, exist_ok=True)


def svg_to_png(svg_path, png_path, scale=None, dpi=None, alpha=False):
    """Convert a SVG file to a PNG file."""
    # I wanted to avoid dependencies that dynamically link to external (i.e.
    # non-python) system libs like cairo, but renderPM does not support
    # transparency when rendering to PNG. The solution used below converts the
    # SVG to PDF with svglib+reportlab, then opens the PDF with fitz (pyMuPdf)
    # and saves it as PNG.
    #
    # The code below is derived from this svglib comment:
    # https://github.com/deeplook/svglib/issues/171#issuecomment-1287829712

    print(f"Generating {png_path} from {svg_path}...")

    if scale is not None and dpi is not None:
        raise ValueError("Cannot specify both scale and dpi")

    # Convert the SVG file to RLG drawing object
    drawing = svglib.svg2rlg(svg_path)
    if drawing is None:
        raise ValueError(f"Failed to convert {svg_path} to ReportLab drawing")

    # If scale is specified, scale the width or height (whichever is larger) to
    # match the scale in pixels, preserving the aspect ratio. If dpi is
    # specified, the drawing will be scaled to the specified dpi.
    if scale is not None:
        max_dimension = max(drawing.width, drawing.height)
        scale_factor = scale / max_dimension
        drawing.width *= scale_factor
        drawing.height *= scale_factor
        drawing.renderScale = scale_factor

    # Render the RLG drawing object to PDF in memory
    pdf = renderPDF.drawToString(drawing)

    # Open the PDF with fitz (pyMuPdf) and save it as a PNG file
    doc = fitz.Document(stream=pdf)
    page = doc.load_page(0)
    pixmap = fitz.utils.get_pixmap(page, alpha=alpha, dpi=dpi)
    ensure_dir(png_path)
    pixmap.save(png_path)


def kicad_version(context):
    """Print the KiCad version."""
    cmd = " ".join(
        [
            KICAD_CLI,
            "version",
            "--format=about",
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: KiCad version check failed with an unexpected exit code ({e.result.exited})"
        )
        raise


def schematic_erc(context, schematic_path, report_path):
    """Run ERC on the schematic."""
    print(f"Running ERC on the schematic...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "sch",
            "erc",
            f"--output={report_path}",
            "--severity-warning",
            "--severity-error",
            "--exit-code-violations",
            f"{schematic_path}",
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        if e.result.exited == 5:
            print(f"\nERROR: ERC violations found in the schematic.")
            print(f"Check {report_path} for details.")
        else:
            # This should not happen unless the KiCad CLI adds additional error
            # return codes in the future.
            print(
                f"\nERROR: ERC failed with an unexpected exit code ({e.result.exited})"
            )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def schematic_export_pdf(context, schematic_path, pdf_path):
    """Export PDF from the schematic."""
    print("Exporting Schematic PDF...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "sch",
            "export",
            "pdf",
            f'--output="{pdf_path}"',
            "--black-and-white",
            "--no-background-color",
            f'"{schematic_path}"',
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: PDF export from the schematic failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def schematic_export_svg(context, schematic_path, svg_path):
    """Export SVG from the schematic."""
    print("Exporting Schematic SVG...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "sch",
            "export",
            "svg",
            f'--output="{svg_path}"',
            "--black-and-white",
            "--no-background-color",
            f'"{schematic_path}"',
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: SVG export from the schematic failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def schematic_export_bom(context, schematic_path, bom_path):
    """Export assembly BOM from the schematic."""
    print("Exporting assembly BOM...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "sch",
            "export",
            "bom",
            f'--output="{bom_path}"',
            '--preset="Common Ground Electronics BOM"',
            '--format-preset="CSV"',
            f'"{schematic_path}"',
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: BOM export from the schematic failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def pcb_drc(context, pcb_path, report_path):
    """Run DRC on the PCB."""
    print(f"Running DRC on the PCB...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "pcb",
            "drc",
            f"--output={report_path}",
            "--schematic-parity",
            "--severity-warning",
            "--severity-error",
            "--exit-code-violations",
            f"{pcb_path}",
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        if e.result.exited == 5:
            print(f"\nERROR: DRC violations found in the PCB.")
            print(f"Check {report_path} for details.")
        else:
            # This should not happen unless the KiCad CLI adds additional error
            # return codes in the future.
            print(
                f"\nERROR: DRC failed with an unexpected exit code ({e.result.exited})"
            )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def pcb_export_gerbers(context, pcb_path, gerbers_path, layers):
    """Export Gerbers from the PCB."""
    print(f"Exporting Gerbers from the PCB...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "pcb",
            "export",
            "gerbers",
            f"--output={gerbers_path}",
            f"--layers={layers}",
            "--exclude-value",
            "--use-drill-file-origin",
            "--no-protel-ext",
            f"{pcb_path}",
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: Gerber export from the PCB failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def pcb_export_odb(context, pcb_path, odb_path):
    """Export ODB++ from the PCB."""
    print(f"Exporting ODB++ from the PCB...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "pcb",
            "export",
            "odb",
            f"--output={odb_path}",
            f"{pcb_path}",
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: Gerber export from the PCB failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def pcb_export_pdf(
    context,
    pcb_path,
    pdf_path,
    layers,
    mirror=False,
    multipage=False,
    black_and_white=True,
):
    """Export PDF from the PCB."""
    print(f"Exporting PDF from the PCB...")
    cmd_list = [
        KICAD_CLI,
        "pcb",
        "export",
        "pdf",
        f"--output={pdf_path}",
        f"--layers={layers}",
        "--exclude-value",
        "--include-border-title",
        "--common-layers=Edge.Cuts",
        "--drill-shape-opt=0",
        f"{pcb_path}",
    ]
    if mirror:
        cmd_list.append(
            "--mirror",
        )
    # The multipage option is currently broken:
    # https://gitlab.com/kicad/code/kicad/-/issues/20726
    if multipage:
        cmd_list.append(
            "--mode-multipage",
        )
    else:
        cmd_list.append(
            "--mode-separate",
        )
    if black_and_white:
        cmd_list.append(
            "--black-and-white",
        )
    cmd = " ".join(cmd_list)
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: PDF export from the PCB failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def pcb_export_drill(context, pcb_path, drill_file_path):
    """Export drill file from the PCB."""
    print(f"Exporting drill file from the PCB...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "pcb",
            "export",
            "drill",
            f"--output={drill_file_path}",
            "--drill-origin=plot",
            "--generate-map",
            f"{pcb_path}",
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: Drill file export from the PCB failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def pcb_export_ipcd356(context, pcb_path, ipcd356_path):
    """Export IPC-D-356 netlist from the PCB."""
    print(f"Exporting IPC-D-356 netlist from the PCB...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "pcb",
            "export",
            "ipcd356",
            f"--output={ipcd356_path}",
            f"{pcb_path}",
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: IPC-D-356 netlist export from the PCB failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def pcb_export_pos(context, pcb_path, position_path):
    """Export position file from the PCB."""
    print(f"Exporting position file from the PCB...")
    cmd = " ".join(
        [
            KICAD_CLI,
            "pcb",
            "export",
            "pos",
            f"--output={position_path}",
            "--use-drill-file-origin",
            f"{pcb_path}",
        ]
    )
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: position file export from the PCB failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


def pcb_render(
    context,
    pcb_path,
    render_path,
    width=1600,
    height=900,
    side="top",
    background="default",
    perspective=False,
    zoom=1,
):
    """Generate render from the PCB."""
    print(f"Generating render from the PCB...")
    cmd_list = [
        KICAD_CLI,
        "pcb",
        "render",
        f"--output={render_path}",
        f"--width={width}",
        f"--height={height}",
        f"--side={side}",
        f"--background={background}",
        f"--zoom={zoom}",
        f"{pcb_path}",
    ]
    if perspective:
        cmd_list.append(
            "--perspective",
        )
    cmd = " ".join(cmd_list)
    try:
        context.run(cmd, echo=True)
    except UnexpectedExit as e:
        print(
            f"\nERROR: IPC-D-356 netlist export from the PCB failed with an unexpected exit code ({e.result.exited})"
        )
        raise  # Re-raise the exception so invoke can handle it and exit cleanly


@task(auto_shortflags=False)
def clean(context, kicad_backups=False, kicad_cache_files=False, all=False):
    """Remove generated files."""

    # Directories
    paths = [
        f"{OUTPUT_PATH}",
    ]

    if kicad_backups or all:
        paths += [
            f"{PROJECT_NAME}-backups",
        ]

    if kicad_cache_files or all:
        paths += [
            "fp-info-cache",
        ]

    for path in paths:
        rm(path, recursive=True, force=True)


@task(auto_shortflags=False)
def env(context):
    """Print project environment info."""
    kicad_version(context)


@task(auto_shortflags=False)
def check(context):
    """Run KiCad checks."""
    schematic_erc(
        context,
        schematic_path=SCH_PATH,
        report_path=ERC_REPORT_PATH,
    )
    pcb_drc(
        context,
        pcb_path=PCB_PATH,
        report_path=DRC_REPORT_PATH,
    )


@task(auto_shortflags=False, pre=[env, check])
def release(context):
    """Generate release files."""
    schematic_export_pdf(
        context,
        schematic_path=SCH_PATH,
        pdf_path=SCH_PDF_PATH,
    )
    schematic_export_svg(
        context,
        schematic_path=SCH_PATH,
        svg_path=SCH_SVG_PATH,
    )
    svg_to_png(
        svg_path=SCH_SVG_PATH / Path(f"{PROJECT_NAME}.svg"),
        png_path=SCH_PNG_PATH.with_suffix(".png"),
        dpi=300,
    )
    svg_to_png(
        svg_path=SCH_SVG_PATH / Path(f"{PROJECT_NAME}.svg"),
        png_path=SCH_PNG_PATH.with_name(f"{SCH_PNG_PATH.stem}_thumbnail.png"),
        scale=500,
    )
    schematic_export_bom(
        context,
        schematic_path=SCH_PATH,
        bom_path=BOM_PATH,
    )
    # Currently need to use the built-in layer names:
    # https://gitlab.com/kicad/code/kicad/-/issues/20904
    pcb_export_gerbers(
        context,
        pcb_path=PCB_PATH,
        gerbers_path=GERBERS_PATH,
        layers="F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,User.Drawings,User.Comments,Edge.Cuts,F.Fab,B.Fab,User.1,User.2",
    )
    # Currently broken when compression is enabled:
    # https://gitlab.com/kicad/code/kicad/-/issues/20891
    # pcb_export_odb(
    #     context,
    #     pcb_path=PCB_PATH,
    #     odb_path=ODB_PATH,
    # )
    pcb_export_drill(
        context,
        pcb_path=PCB_PATH,
        drill_file_path=DRILL_FILES_PATH,
    )
    pcb_export_ipcd356(
        context,
        pcb_path=PCB_PATH,
        ipcd356_path=IPCD356_PATH,
    )
    # Currently need to use the built-in layer names:
    # https://gitlab.com/kicad/code/kicad/-/issues/20904
    pcb_export_pdf(
        context,
        pcb_path=PCB_PATH,
        pdf_path=PCB_PDF_PATH,
        layers="F.Cu,F.Paste,F.Silkscreen,F.Mask,User.Drawings,User.Comments,Edge.Cuts,F.Fab,User.1",
    )
    # Currently need to use the built-in layer names:
    # https://gitlab.com/kicad/code/kicad/-/issues/20904
    pcb_export_pdf(
        context,
        pcb_path=PCB_PATH,
        pdf_path=PCB_PDF_PATH,
        layers="B.Cu,B.Paste,B.Silkscreen,B.Mask,B.Fab,User.2",
        mirror=True,
    )
    pcb_export_pos(
        context,
        pcb_path=PCB_PATH,
        position_path=POSITION_PATH,
    )
    # There are a few issues with the KiCad CLI render command that need to be
    # resolved before this can be enabled. For example, it's not possible to
    # customize the layers that are rendered and it's not possible to use a
    # custom preset. Some related issues:
    # https://gitlab.com/kicad/code/kicad/-/issues/20660
    # https://gitlab.com/kicad/code/kicad/-/issues/20719
    #
    # pcb_render(
    #     context,
    #     pcb_path=PCB_PATH,
    #     render_path=PCA_RENDER_PATH
    #     / Path(
    #         f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_PCA_{PCA_PART_NUMBER}_Rev_{PCA_REV}_top_ortho.png"
    #     ),
    #     width=1000,
    #     height=800,
    #     zoom=1,
    #     side="top",
    #     perspective=True,
    # )
    # pcb_render(
    #     context,
    #     pcb_path=PCB_PATH,
    #     render_path=PCA_RENDER_PATH
    #     / Path(
    #         f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_PCA_{PCA_PART_NUMBER}_Rev_{PCA_REV}_bottom_ortho.png"
    #     ),
    #     width=1000,
    #     height=800,
    #     zoom=1,
    #     side="bottom",
    #     perspective=True,
    # )
    # pcb_render(
    #     context,
    #     pcb_path=PCB_PATH,
    #     render_path=PCA_RENDER_PATH
    #     / Path(
    #         f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_PCA_{PCA_PART_NUMBER}_Rev_{PCA_REV}_top.png"
    #     ),
    #     width=1000,
    #     height=800,
    #     zoom=1,
    #     side="top",
    #     perspective=False,
    # )
    # pcb_render(
    #     context,
    #     pcb_path=PCB_PATH,
    #     render_path=PCA_RENDER_PATH
    #     / Path(
    #         f"{PROJECT_NAME}_v{PROJECT_VERSION_MAJOR}_PCA_{PCA_PART_NUMBER}_Rev_{PCA_REV}_bottom.png"
    #     ),
    #     width=1000,
    #     height=800,
    #     zoom=1,
    #     side="bottom",
    #     perspective=False,
    # )
