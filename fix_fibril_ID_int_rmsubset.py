#!/usr/bin/env python3
"""
fix_fibrilID_2.py
- Update _rlnHelicalTubeID with closest match
- Remove _rlnRandomSubset #30 + values
- Last 2 digits → integer → 0 becomes 1
"""
## example:
## python fix_fibrilID_int_rmsubst.py Select/job068/particles.star ../relion/J45/J45_020_particles_csfID_output/ .star
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
from scipy.spatial import KDTree

# ----------------------------------------------------------------------
# 1. Parse STAR
# ----------------------------------------------------------------------
def parse_star_particles(
    star_path: Path,
) -> Tuple[List[Dict], Dict[str, int], List[str]]:
    with star_path.open("r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]

    in_block = False
    field_to_idx: Dict[str, int] = {}
    particles: List[Dict] = []
    header_lines: List[str] = []

    for line in lines:
        stripped = line.strip()

        # ----- block detection ------------------------------------------------
        if stripped.startswith("data_particles") or stripped.startswith("data_"):
            in_block = True
            field_to_idx = {}
            header_lines.append(line)
            continue
        if stripped.startswith("data_") and in_block:
            in_block = False

        if not in_block:
            header_lines.append(line)
            continue

        # ----- skip _rlnRandomSubset in header -------------------------------
        if stripped.startswith("_rlnRandomSubset"):
            header_lines.append(line)
            continue

        # ----- column definitions (skip _rlnRandomSubset) --------------------
        if stripped.startswith("_rln"):
            parts = stripped.split()
            if len(parts) >= 2 and "_rlnRandomSubset" not in parts[0]:
                field = parts[0]
                try:
                    idx = int(parts[1].lstrip("#")) - 1
                    field_to_idx[field] = idx
                except ValueError:
                    pass
            header_lines.append(line)
            continue

        # ----- loop_, comments, empty ----------------------------------------
        if stripped.startswith("loop_") or not stripped or stripped.startswith("#"):
            header_lines.append(line)
            continue

        # ----- data row ------------------------------------------------------
        vals = line.split()
        x_idx = field_to_idx.get("_rlnCoordinateX")
        y_idx = field_to_idx.get("_rlnCoordinateY")
        fid_idx = field_to_idx.get("_rlnHelicalTubeID")

        if x_idx is None or y_idx is None or fid_idx is None:
            continue
        if len(vals) <= max(x_idx, y_idx, fid_idx):
            continue

        try:
            x = float(vals[x_idx])
            y = float(vals[y_idx])
            fid = vals[fid_idx]
        except ValueError:
            continue

        # Exclude last column (_rlnRandomSubset)
        original_vals = vals[:-1]

        particles.append(
            {
                "x": x,
                "y": y,
                "fid": fid,
                "raw_line": line,
                "fid_idx": fid_idx,
                "original_vals": original_vals,
            }
        )

    return particles, field_to_idx, header_lines


# ----------------------------------------------------------------------
# 2. Extract micrograph base name
# ----------------------------------------------------------------------
MICROGRAPH_RE = re.compile(r"([^/\\]+)\.(mrc|mrcs)$", re.IGNORECASE)


def get_micrograph_base(micrograph_name: str) -> str:
    m = MICROGRAPH_RE.search(micrograph_name)
    return m.group(1) if m else ""


# ----------------------------------------------------------------------
# 3. Convert fibril ID → last 2 digits → clean int → 0 → 1
# ----------------------------------------------------------------------
def shorten_fid_to_int(fid: str) -> int:
    """
    Take last 2 digits → convert to int → if 0, return 1
    e.g. '4096956178922071108' → 8
         '100'                 → 0 → 1
         '123'                 → 23
    """
    try:
        last_two = str(int(fid))[-2:]
        value = int(last_two)
        return 1 if value == 0 else value
    except (ValueError, IndexError):
        return 1  # fallback


# ----------------------------------------------------------------------
# 4. Main
# ----------------------------------------------------------------------
def main() -> None:
    if len(sys.argv) != 4:
        prog = Path(sys.argv[0]).name
        print(f"Usage: {prog} <main.star> <corr_folder> <suffix>")
        sys.exit(1)

    main_star = Path(sys.argv[1])
    corr_folder = Path(sys.argv[2])
    suffix = sys.argv[3].lstrip(".")

    if not main_star.is_file():
        print(f"Error: main file not found → {main_star}", file=sys.stderr)
        sys.exit(1)
    if not corr_folder.is_dir():
        print(f"Error: correspond folder not found → {corr_folder}", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Parse main file
    # ------------------------------------------------------------------
    print("Parsing main STAR file...", file=sys.stderr)
    main_particles, main_field_to_idx, header_lines = parse_star_particles(main_star)

    mic_idx = main_field_to_idx.get("_rlnMicrographName")
    if mic_idx is None:
        print("Error: _rlnMicrographName not found in main STAR", file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Map micrograph base → particles
    # ------------------------------------------------------------------
    micrograph_to_particles: Dict[str, List[Dict]] = {}
    with main_star.open("r") as f:
        lines = f.readlines()

    in_block = False
    row_idx = 0
    for raw in lines:
        line = raw.strip()

        if line.startswith("data_particles"):
            in_block = True
            continue
        if line.startswith("data_") and in_block:
            in_block = False

        if not in_block:
            continue

        if line.startswith("_rln") or not line or line.startswith("#") or line.startswith("loop_"):
            continue

        vals = line.split()
        if len(vals) <= mic_idx:
            row_idx += 1
            continue

        mic_name = vals[mic_idx]
        base = get_micrograph_base(mic_name)
        if not base:
            row_idx += 1
            continue

        if row_idx < len(main_particles):
            p = main_particles[row_idx]
            p["micrograph_base"] = base
            micrograph_to_particles.setdefault(base, []).append(p)

        row_idx += 1

        if row_idx >= 200000:          # stop after 1000 data lines
            break

    # ------------------------------------------------------------------
    # Load correspond files
    # ------------------------------------------------------------------
    corr_trees: Dict[str, Tuple[KDTree, List[Dict]]] = {}
    for base in micrograph_to_particles.keys():
        corr_path = corr_folder / f"{base}.{suffix}"
        if not corr_path.is_file():
            print(f"Warning: missing → {corr_path.name}", file=sys.stderr)
            continue

        corr_parts, _, _ = parse_star_particles(corr_path)
        if not corr_parts:
            continue

        coords = np.array([[p["x"], p["y"]] for p in corr_parts])
        tree = KDTree(coords)
        corr_trees[base] = (tree, corr_parts)

    # ------------------------------------------------------------------
    # Update fibril IDs → last 2 digits → 0 → 1
    # ------------------------------------------------------------------
    updated = 0
    skipped = 0
    zero_to_one = 0

    for base, particles in micrograph_to_particles.items():
        if base not in corr_trees:
            skipped += len(particles)
            continue

        tree, corr_parts = corr_trees[base]
        for p in particles:
            query = np.array([[p["x"], p["y"]]])
            _, idx = tree.query(query, k=1)
            new_fid_long = corr_parts[idx[0]]["fid"]
            new_fid_int = shorten_fid_to_int(new_fid_long)

            if new_fid_int == 1 and str(int(p["fid"]))[-2:] == "00":
                zero_to_one += 1

            if str(p["fid"]) != str(new_fid_int):
                updated += 1

            # Rebuild line
            vals = p["original_vals"].copy()
            vals[p["fid_idx"]] = str(new_fid_int)
            p["updated_line"] = " ".join(vals)

    # ------------------------------------------------------------------
    # Write output
    # ------------------------------------------------------------------
    output_path = main_star.with_name(main_star.stem + "_updated_intID_2.star")
    with main_star.open("r") as f_in, output_path.open("w", encoding="utf-8") as f_out:
        in_data_block = False
        particle_idx = 0

        for line in f_in:
            stripped = line.strip()

            if not in_data_block:
                if stripped.startswith("data_particles"):
                    in_data_block = True
                if "_rlnRandomSubset" in stripped:
                    continue
                f_out.write(line)
                continue

            if (
                stripped.startswith("_rln")
                or stripped.startswith("loop_")
                or not stripped
                or stripped.startswith("#")
            ):
                if "_rlnRandomSubset" in stripped:
                    continue
                f_out.write(line)
                continue

            if particle_idx < len(main_particles):
                p = main_particles[particle_idx]
                if "updated_line" in p:
                    f_out.write(p["updated_line"] + "\n")
                else:
                    f_out.write(" ".join(line.strip().split()[:-1]) + "\n")
                particle_idx += 1
            else:
                f_out.write(" ".join(line.strip().split()[:-1]) + "\n")

    print("\nDone!")
    print(f"Output written to: {output_path}")
    print(f"Particles updated (ID changed): {updated}")
    print(f"Particles skipped (no correspond file): {skipped}")
    print(f"IDs ending in '00' → changed to 1: {zero_to_one}")
    print(f"Final fibril IDs: 1–99 (0 → 1)")


if __name__ == "__main__":
    main()

