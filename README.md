# Offline CBR Tune Analyzer (starter)

This is a small offline, read-only analysis tool. It accepts a wideband logger
CSV and groups samples into RPM/TPS cells, reporting the median AFR and a
review-only estimated fuel trim. It does **not** communicate with a motorcycle,
modify a map, or write ECU/controller data.

## Run

Requires Python 3.10+ and no third-party packages.

```sh
python analyze.py sample_wideband.csv --target-afr 13.2 -o suggestions.csv
python -m unittest discover -s tests -v
```

Input headers must include `rpm`, `tps`, and `afr`. Extra columns are ignored.
The provided target is a demonstration value, not a recommendation for every
operating condition. A real tune needs a valid target AFR table, calibrated
wideband data, controlled load, and review by a qualified tuner. Do not use
public-road pulls to collect high-load data.

The estimated trim formula is `(observed AFR / target AFR - 1) * 100`. It is
only a rough cell-level suggestion; it does not account for transient behavior,
closed-loop correction, temperature, fuel composition, sensor delay, or the
controller's map conventions. Never upload these suggestions directly.
