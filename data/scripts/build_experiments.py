# experiments.json from the pasted PSI search page (psi.nasa.gov/physci/repo/search?q=combustion, page 1 of 2, 25 of 26 results).
# Copied from the page: id, title, research area, project type, objective text. Everything marked "judgement" is ours.
import os
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # scripts live in data/scripts/
import json
D = DATA_DIR
# id, title, project_type, fuel_type (judgement), one-sentence summary (ours, from the page's objective text), highlights keywords
R = [
("PSI-117","Effect of External Thermo-Convective Perturbation on Cool Flame Dynamics: A Multidimensional Multi-Physics CFD Analysis","Ground","liquid","Uses NASA's FLEX flight data to model how outside heat and airflow disturbances change cool flames around liquid fuel droplets."),
("PSI-159","Advanced Combustion via Microgravity Experiments / Cool Flames Investigation with Gases (ACME CFI-G)","Microgravity","gas","Flies spherical gas flames on the space station to find when cool diffusion flames occur for propane, n-butane and n-pentane."),
("PSI-10","Advanced Combustion via Microgravity Experiments / Flame Design (ACME/Flame Design)","Microgravity","gas","Measures when spherical gas flames start making soot, as flow rate and dilution change, in drop towers and on the space station."),
("PSI-62","Concurrent Flame Spread Modeling using Flamelet Generated Manifolds in Microgravity with Comparison to BASS Experiments using Two-Color Tomography","Ground","solid","Builds and tests computer models of flame spreading in the same direction as the airflow in microgravity, compared with BASS results."),
("PSI-60","Computational and Experimental Analysis of SPICE Data Sets","Ground","gas","Analyzes SPICE images and soot models to understand why soot forms differently in normal gravity and microgravity flames."),
("PSI-142","Quantitative Studies of Cool Flame Transitions at Radiation / Stretch Extinction Using Counterflow Flames","Ground","liquid","Uses FLEX flight data with new simulations to study how oxygen level affects the point where cool flames go out."),
("PSI-101","Smoke Aerosol Measurement Experiment-Reflight (SAME-R)","Microgravity","other","Reflight of SAME to measure the sizes of smoke particles in low gravity, with a new fire-retardant test material."),
("PSI-115","Utilization of the Smoke Aerosol Measurement Experiment Data for Advanced Modeling and Simulation of Smoke Generation in Micro-Gravity","Ground","other","Simulates how smoke particles form and grow in Earth gravity and microgravity."),
("PSI-98","Spacecraft Fire Safety Experiment-I (SAFFIRE-I)","Microgravity","solid","Burned a large fabric sample on a Cygnus spacecraft to see how fast a big fire grows in low gravity and how its flammability limits compare to NASA's normal-gravity test."),
("PSI-39","Cool Flames Investigation (CFI)","Microgravity","liquid","Studies how n-dodecane droplets burn as cool flames at pressures from 0.25 to 5 atmospheres."),
("PSI-102","Smoke and Aerosol Measurement Experiment (SAME)","Microgravity","other","Measured how big smoke particles get in low gravity and how that relates to smoke generation."),
("PSI-106","Structure and Liftoff In Combustion Experiment (SLICE)","Microgravity","gas","Studies the structure and stability of small gas diffusion flames in microgravity."),
("PSI-99","Spacecraft Fire Experiment-II (SAFFIRE-II)","Microgravity","solid","Second Cygnus fire experiment, measuring how fast a large fire grows in low gravity and its flammability limits."),
("PSI-107","Smoke Point In Co-flow Experiment (SPICE)","Microgravity","gas","Observes gas flames on the space station to understand soot and smoke production."),
("PSI-100","Spacecraft Fire Experiment-III (SAFFIRE-III)","Microgravity","solid","Third Cygnus fire experiment, measuring how fast a large fire grows in low gravity and its flammability limits."),
("PSI-21","Advanced Combustion via Microgravity Experiments / Coflow Laminar Diffusion Flame (ACME CLD Flame)","Microgravity","gas","Provides flame data, from very dilute to sooty, for testing computer models of gas diffusion flames."),
("PSI-25","Burning and Suppression of Solids - II (BASS-II)","Microgravity","solid","Burns solid samples such as fabric and plastic rods in a space station wind tunnel to study ignition, flame spread and extinction for fire-safety models."),
("PSI-20","Advanced Combustion via Microgravity Experiments - Burning Rate Emulator (ACME BRE)","Microgravity","gas","Uses a gas burner that imitates a burning solid to learn how fuel properties set the burning rate in still microgravity air."),
("PSI-68","Flame Extinguishment Experiment - 2 (FLEX-2)","Microgravity","liquid","Extends FLEX to fuels and conditions closer to real combustors, with oxygen from 0.1 to 0.4 mole fraction and pressures from 0.5 to 3 atmospheres."),
("PSI-22","Advanced Combustion via Microgravity Experiments Electric-Field Effects on Laminar Diffusion Flames (ACME E-FIELD Flames)","Microgravity","gas","Studies how electric fields change the behavior of gas diffusion flames in microgravity."),
("PSI-23","Advanced Combustion via Microgravity Experiments - Structure and Response of Spherical Diffusion Flames (ACME s-Flame)","Microgravity","gas","Burns gas fuels from a spherical burner to compare with detailed flame simulations."),
("PSI-69","Flame Extinguishment Experiment (FLEX)","Microgravity","liquid","Maps the flammability limits of liquid fuel droplets in microgravity and tests how well different suppressant gases work."),
("PSI-26","Burning and Suppression of Solids (BASS)","Microgravity","solid","Burned fabric samples (75% cotton, 25% fiberglass) on the space station to link NASA's standard normal-gravity test to real microgravity flammability."),
]
VERIFIED_COUNT = {"PSI-25": (129, "our PSI-25 table, counted by code"), "PSI-98": (2, "our PSI-98 table, counted by code"),
                  "PSI-99": (10, "our PSI-99 table, counted by code (one sample row split in two)"), "PSI-100": (2, "our PSI-100 table, counted by code")}
HAS_TABLE_PLAN = {"PSI-20","PSI-21","PSI-25","PSI-26","PSI-47","PSI-98","PSI-99","PSI-100"}  # the team plan lists these as having table CSVs
out = []
for pid, title, ptype, fuel, summ in R:
    n = pid.split("-")[1]
    flight = ptype != "Ground"
    tc = VERIFIED_COUNT.get(pid)
    out.append({"psi_id": pid, "title": title,
        "url": f"https://psi.nasa.gov/geode-py/ws/repo/investigations/{pid}",
        "url_note": "PSI record (JSON) link given in the team plan; the human landing-page URL is not confirmed",
        "research_area": "Combustion Science", "project_type": ptype + (" Investigation"),
        "fuel_type": fuel, "fuel_type_basis": "judgement from title and objective text",
        "gravity": "ground" if not flight else "micro", "is_flight": flight,
        "has_data_table": True if pid in HAS_TABLE_PLAN else None,
        "has_data_table_note": "team plan lists a table CSV for this id" if pid in HAS_TABLE_PLAN else "not checked: PSI page not opened for this id",
        "test_count": tc[0] if tc else None, "test_count_source": tc[1] if tc else "not counted (no table of ours for this id)",
        "summary": summ, "summary_basis": "written by us from the objective text on the PSI search page (the page text is cut off)",
        "score": None, "score_breakdown": [], "score_note": "left for Lane B to score"})
assert len(out) == 23 and len({o["psi_id"] for o in out}) == 23
json.dump(out, open(f"{D}/experiments.json", "w"), indent=1)
print(len(out), "experiments;", sum(o["is_flight"] for o in out), "flight")
