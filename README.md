# StatNotes

StatNotes analyzes concert attendee feedback from a CSV file. It summarizes attendee ages and satisfaction, favorite songs and artists, return intentions, and age-group results. It can also save charts and a summary CSV.

## Requirements

- Python 3.10 or later
- pandas
- matplotlib

Install the required packages:

```bash
python -m pip install -r requirements.txt
```

## Input CSV

The input CSV must include:

- An age column, such as `age` or `attendee_age`
- A satisfaction column, such as `satisfaction`, `rating`, or `satisfaction_rating`
- Either a `favorites` column, or both an artist column and a song column

Column names are matched case-insensitively after normalization. For example, `Favorite Artist` is accepted as `favorite_artist`.

Optional columns can record return intention and the reason for not returning. Return-intention columns include `return_intention`, `would_return`, and `intend_to_return`. Reason columns include `reason` and `reason_not_returning`.

For a `favorites` value, use `Artist - Song` to provide both the artist and song. If there is no ` - ` separator, StatNotes treats the entire value as a song.

A sample input file is included as `sample_concert_data.csv`.

## Run

Analyze the sample file, save the summary as `concert_summary.csv`, and save charts in a `charts` folder:

```bash
python StatNotes.py \
  --input sample_concert_data.csv \
  --output concert_summary.csv \
  --output-dir charts
```

To see all command-line options:

```bash
python StatNotes.py --help
```

Use `--no-plots` to skip chart creation:

```bash
python StatNotes.py --input sample_concert_data.csv --no-plots
```

## Output

The program prints a report in the terminal and saves a summary CSV. By default, it also creates charts for attendee ages, favorite songs, and favorite artists.

Age groups are `0–17`, `18–34`, `35–54`, and `55+`. Ages outside 0–120 and non-numeric ages are excluded from age statistics.

Return-intention percentages are calculated from recognized yes/no responses only. The program recognizes `yes`, `y`, `true`, `1`, `likely`, and `definitely` as yes; it recognizes `no`, `n`, `false`, `0`, `unlikely`, and `never` as no. Other nonblank answers are reported as unrecognized.

## Tests

Run the test suite with:

```bash
python -m pytest -v
```

## License

Add your chosen license here before distributing or reusing this project.

