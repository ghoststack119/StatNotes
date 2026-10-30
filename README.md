# StatNotes

StatNotes is a Python tool for analyzing concert feedback from CSV files. It summarizes audience demographics and return intent, counts favorite songs and artists, and generates charts.

## Features

- Groups ages into **0–17**, **18–34**, **35–54**, and **55+**.
- Counts favorite songs and artists case-insensitively while preserving the first spelling entered for display.
- Normalizes column headers to case-insensitive `snake_case`.
- Maps common return-intention answers, such as `yes`, `likely`, `no`, and `never`, into yes/no categories.
- Reports unrecognized return-intention responses instead of silently treating them as yes or no.
- Saves charts to a configurable output directory.

## Requirements

- Python 3
- pandas
- matplotlib

## Setup

Clone the repository and enter its directory:

```bash
git clone https://github.com/ghoststack119/StatNotes.git
cd StatNotes
