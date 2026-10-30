from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd


AGE_GROUPS = ["0–17", "18–34", "35–54", "55+"]


def normalize_header(header: Any) -> str:
    """Normalize a column name to lowercase snake_case."""
    text = str(header).strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with normalized headers; reject duplicate results."""
    result = df.copy()
    result.columns = [normalize_header(column) for column in result.columns]

    duplicates = result.columns[result.columns.duplicated()].tolist()
    if duplicates:
        raise ValueError(
            f"Duplicate column names after normalization: {duplicates}"
        )

    return result


def clean_text(value: Any) -> str | None:
    """Return trimmed text, or None for missing or blank values."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()
    return text or None


def find_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    """Find the first column matching one of the provided aliases."""
    for alias in aliases:
        normalized = normalize_header(alias)
        if normalized in df.columns:
            return normalized
    return None


class ConcertAnalyzer:
    """Analyze concert attendee feedback stored in a pandas DataFrame."""

    def __init__(self, df: pd.DataFrame):
        self.df = normalize_columns(df)

        self.age_col = find_column(self.df, ["age", "attendee_age"])
        self.satisfaction_col = find_column(
            self.df,
            [
                "satisfaction",
                "satisfaction_level",
                "rating",
                "satisfaction_rating",
            ],
        )
        self.favorites_col = find_column(
            self.df, ["favorites", "favorite", "favourite"]
        )
        self.artist_col = find_column(
            self.df, ["artist", "favorite_artist", "favourite_artist"]
        )
        self.song_col = find_column(
            self.df, ["song", "favorite_song", "favourite_song"]
        )
        self.return_col = find_column(
            self.df,
            [
                "return_intention",
                "intend_to_return",
                "would_return",
                "returning",
            ],
        )
        self.reason_col = find_column(
            self.df,
            [
                "reason",
                "reason_not_returning",
                "reason_for_not_returning",
                "non_return_reason",
            ],
        )

        missing = []
        if self.age_col is None:
            missing.append("age")
        if self.satisfaction_col is None:
            missing.append("satisfaction")
        if self.favorites_col is None and (
            self.artist_col is None or self.song_col is None
        ):
            missing.append("favorites, or both artist and song")

        if missing:
            raise ValueError("Missing required column(s): " + ", ".join(missing))

        self.df["_age"] = pd.to_numeric(
            self.df[self.age_col], errors="coerce"
        )
        self.df["_age"] = self.df["_age"].where(
            self.df["_age"].between(0, 120)
        )

        self.df["_satisfaction"] = pd.to_numeric(
            self.df[self.satisfaction_col], errors="coerce"
        )

        # Ranges: 0 <= age < 18, 18 <= age < 35,
        # 35 <= age < 55, and 55 <= age <= 120.
        self.df["_age_group"] = pd.cut(
            self.df["_age"],
            bins=[0, 18, 35, 55, 121],
            labels=AGE_GROUPS,
            right=False,
        )

        self.songs, self.artists = self._get_favorites()

    def _get_favorites(self) -> tuple[pd.Series, pd.Series]:
        """Extract favorite song and artist values from the available columns."""
        songs: list[str | None] = []
        artists: list[str | None] = []

        for _, row in self.df.iterrows():
            artist = None
            song = None

            if self.favorites_col is not None:
                favorite = clean_text(row[self.favorites_col])
                if favorite:
                    if " - " in favorite:
                        artist_text, song_text = favorite.split(" - ", 1)
                        artist = clean_text(artist_text)
                        song = clean_text(song_text)
                    else:
                        # Without " - ", treat the value as a song.
                        song = favorite
            else:
                artist = clean_text(row[self.artist_col])
                song = clean_text(row[self.song_col])

            artists.append(artist)
            songs.append(song)

        return (
            pd.Series(songs, index=self.df.index, dtype="object"),
            pd.Series(artists, index=self.df.index, dtype="object"),
        )

    @staticmethod
    def _counts(values: pd.Series) -> pd.Series:
        """Count nonblank values case-insensitively, preserving first spelling."""
        cleaned = values.map(clean_text).dropna()

        if cleaned.empty:
            return pd.Series(dtype="int64")

        display_names: dict[str, str] = {}
        for value in cleaned:
            display_names.setdefault(value.casefold(), value)

        counts = cleaned.map(str.casefold).value_counts()
        counts.index = [display_names[key] for key in counts.index]
        return counts

    @staticmethod
    def _numeric_stats(values: pd.Series) -> dict[str, float | int | None]:
        """Calculate basic statistics after excluding missing values."""
        valid = values.dropna()

        if valid.empty:
            return {
                "count": 0,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
            }

        return {
            "count": int(valid.count()),
            "mean": float(valid.mean()),
            "median": float(valid.median()),
            "min": float(valid.min()),
            "max": float(valid.max()),
        }

    def age_stats(self) -> dict[str, float | int | None]:
        """Return statistics for valid ages."""
        return self._numeric_stats(self.df["_age"])

    def satisfaction_stats(self) -> dict[str, float | int | None]:
        """Return statistics for numeric satisfaction responses."""
        return self._numeric_stats(self.df["_satisfaction"])

    def age_group_stats(self) -> pd.DataFrame:
        """Summarize attendees with valid ages, including empty age groups."""
        valid = self.df.loc[self.df["_age_group"].notna()].copy()
        valid["_song"] = self.songs.loc[valid.index]
        valid["_artist"] = self.artists.loc[valid.index]

        grouped = valid.groupby("_age_group", observed=False)
        result = grouped.agg(
            attendees=("_age", "size"),
            average_satisfaction=("_satisfaction", "mean"),
        )

        def most_common(values: pd.Series) -> str | None:
            counts = self._counts(values)
            return str(counts.index[0]) if not counts.empty else None

        result["favorite_song"] = grouped["_song"].agg(most_common)
        result["favorite_artist"] = grouped["_artist"].agg(most_common)
        return result

    @staticmethod
    def return_stats(
        df: pd.DataFrame,
        return_col: str | None,
        reason_col: str | None,
    ) -> dict[str, Any]:
        """Summarize recognized yes/no responses and reasons for no responses."""
        empty_result = {
            "responses": 0,
            "yes_count": 0,
            "yes_percentage": None,
            "no_count": 0,
            "no_percentage": None,
            "unrecognized_count": 0,
            "reasons": {},
        }

        if return_col is None:
            return empty_result

        normalized = df[return_col].map(clean_text)
        normalized = normalized.map(
            lambda value: value.casefold() if isinstance(value, str) else None
        )

        yes_values = {"yes", "y", "true", "1", "likely", "definitely"}
        no_values = {"no", "n", "false", "0", "unlikely", "never"}

        yes_mask = normalized.isin(yes_values)
        no_mask = normalized.isin(no_values)
        answered_mask = normalized.notna()
        recognized_mask = yes_mask | no_mask

        yes_count = int(yes_mask.sum())
        no_count = int(no_mask.sum())
        response_count = yes_count + no_count
        unrecognized_count = int((answered_mask & ~recognized_mask).sum())

        reasons: dict[str, int] = {}
        if reason_col is not None and no_mask.any():
            reason_values = df.loc[no_mask, reason_col].map(clean_text).dropna()
            reasons = {
                str(reason): int(count)
                for reason, count in reason_values.value_counts().items()
            }

        return {
            "responses": response_count,
            "yes_count": yes_count,
            "yes_percentage": (
                100 * yes_count / response_count if response_count else None
            ),
            "no_count": no_count,
            "no_percentage": (
                100 * no_count / response_count if response_count else None
            ),
            "unrecognized_count": unrecognized_count,
            "reasons": reasons,
        }

    def summary_rows(self) -> list[dict[str, Any]]:
        """Convert analysis results into rows suitable for a summary CSV."""
        rows: list[dict[str, Any]] = []

        for category, stats in (
            ("age", self.age_stats()),
            ("satisfaction", self.satisfaction_stats()),
        ):
            for metric, value in stats.items():
                rows.append(
                    {"category": category, "metric": metric, "value": value}
                )

        returns = self.return_stats(
            self.df, self.return_col, self.reason_col
        )
        for metric in (
            "responses",
            "yes_count",
            "yes_percentage",
            "no_count",
            "no_percentage",
            "unrecognized_count",
        ):
            rows.append(
                {
                    "category": "return_intention",
                    "metric": metric,
                    "value": returns[metric],
                }
            )

        for reason, count in returns["reasons"].items():
            rows.append(
                {
                    "category": "non_return_reason",
                    "metric": reason,
                    "value": count,
                }
            )

        for song, count in self._counts(self.songs).items():
            rows.append(
                {
                    "category": "favorite_song",
                    "metric": song,
                    "value": int(count),
                }
            )

        for artist, count in self._counts(self.artists).items():
            rows.append(
                {
                    "category": "favorite_artist",
                    "metric": artist,
                    "value": int(count),
                }
            )

        for group, values in self.age_group_stats().iterrows():
            for metric, value in values.items():
                rows.append(
                    {
                        "category": f"age_group_{group}",
                        "metric": metric,
                        "value": value,
                    }
                )

        return rows

    def save_summary(self, output_path: str | Path) -> None:
        """Save the analysis summary as a CSV file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(self.summary_rows()).to_csv(path, index=False)

    @staticmethod
    def _plot_counts(
        counts: pd.Series,
        title: str,
        filename: Path,
        top: int,
    ) -> None:
        """Save a horizontal bar chart of the most common values."""
        if counts.empty:
            return

        selected = counts.head(top).sort_values()
        plt.figure(figsize=(10, max(4, len(selected) * 0.35)))
        selected.plot(kind="barh")
        plt.title(title)
        plt.xlabel("Number of mentions")
        plt.tight_layout()
        plt.savefig(filename)
        plt.close()

    def create_plots(self, top: int = 10, output_dir: str | Path = ".") -> None:
        """Save age and favorite charts in the specified directory."""
        if top < 1:
            raise ValueError("top must be at least 1")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        ages = self.df["_age"].dropna()
        if not ages.empty:
            plt.figure()
            plt.hist(ages, bins=12, edgecolor="black")
            plt.title("Concert Attendee Age Distribution")
            plt.xlabel("Age")
            plt.ylabel("Number of attendees")
            plt.tight_layout()
            plt.savefig(output_dir / "age_distribution.png")
            plt.close()

        self._plot_counts(
            self._counts(self.songs),
            "Favorite Songs",
            output_dir / "favorite_songs.png",
            top,
        )
        self._plot_counts(
            self._counts(self.artists),
            "Favorite Artists",
            output_dir / "favorite_artists.png",
            top,
        )

    def print_report(self) -> None:
        """Print a readable summary of the analysis."""
        print("Concert Feedback Summary")
        print("------------------------")

        age = self.age_stats()
        print(f"Valid ages: {age['count']}")
        if age["mean"] is not None:
            print(
                f"Age: mean {age['mean']:.1f}, median {age['median']:.1f}, "
                f"range {age['min']}–{age['max']}"
            )

        satisfaction = self.satisfaction_stats()
        print(f"Valid satisfaction responses: {satisfaction['count']}")
        if satisfaction["mean"] is not None:
            print(
                f"Satisfaction: mean {satisfaction['mean']:.2f}, "
                f"median {satisfaction['median']:.2f}"
            )

        returns = self.return_stats(
            self.df, self.return_col, self.reason_col
        )
        if returns["responses"]:
            print(
                f"Would return: {returns['yes_percentage']:.1f}% yes, "
                f"{returns['no_percentage']:.1f}% no"
            )

        if returns["unrecognized_count"]:
            print(
                "Unrecognized return-intention responses: "
                f"{returns['unrecognized_count']}"
            )

        if returns["reasons"]:
            print("Reasons given by attendees who would not return:")
            for reason, count in returns["reasons"].items():
                print(f"  {reason}: {count}")

        print("\nAge-group breakdown:")
        print(self.age_group_stats().to_string())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze concert feedback stored in a CSV file."
    )
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Maximum number of favorites to chart (default: 10)",
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip creating charts",
    )
    parser.add_argument(
        "--output",
        default="concert_summary.csv",
        help="Summary CSV path (default: concert_summary.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory for charts (default: current directory)",
    )
    args = parser.parse_args()

    if args.top < 1:
        parser.error("--top must be at least 1")

    try:
        data = pd.read_csv(args.input)
        analyzer = ConcertAnalyzer(data)
        analyzer.print_report()
        analyzer.save_summary(args.output)

        if not args.no_plots:
            analyzer.create_plots(args.top, output_dir=args.output_dir)

        print(f"\nSummary saved to {args.output}")
        if not args.no_plots:
            print(f"Charts saved in {args.output_dir}.")

    except (OSError, pd.errors.ParserError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
