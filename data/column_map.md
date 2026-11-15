# PSI-25 column map (SI note: written with SI assistance (Claude), reviewed by <name>)
Read from the actual file header, 17 columns.
| # | PSI-25 column | Feeds contract field |
|---|---|---|
| 1 | PI | not plotted (raw_pi) |
| 2 | Test # | id (with GMT); join key to Zhao |
| 3 | Date | raw_date only, do not rely on it |
| 4 | GMT | id (with Test #); join key to Zhao |
| 5 | Sample # | sample_id |
| 6 | Fuel Sample Material | material + shape (original in raw_material) |
| 7 | Flow restrictor | not plotted (raw_flow_restrictor) |
| 8 | Fan display | not plotted (raw_fan_display); fan setting, not cm/s |
| 9 | Air display | flow_start / flow_end (original in raw_air_display); this is the cm/s column |
| 10 | Radiometer gain   (1000   250   50   10) | not plotted |
| 11 | Total Frames Shot | not plotted |
| 12 | Calibrated  initial O2 % by vol | o2_start |
| 13 | Calibrated final O2 % by vol | o2_end |
| 14 | Initial CO2 % by vol | not plotted (raw) |
| 15 | Final CO2 % by vol | not plotted (raw) |
| 16 | Initial CO (ppm) | not plotted (raw) |
| 17 | Final CO (ppm) | not plotted (raw) |
