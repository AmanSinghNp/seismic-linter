

from seismic_linter.analyzer import analyze_file

def test_analyze_file_notebook(tmp_path):
    """End-to-end test for analyzing a notebook file via public API."""
    nb_content = r"""
{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "df = pd.DataFrame({'a': [1]})\n",
    "df['b'] = df['a'].mean()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.8.5"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}
"""
    nb_file = tmp_path / "test.ipynb"
    nb_file.write_text(nb_content.strip(), encoding="utf-8")

    violations = analyze_file(nb_file)
    
    # Should have T001 on the last line of the cell
    assert len(violations) >= 1
    v = next(v for v in violations if v.rule_id == "T001")
    
    assert v.filename == str(nb_file)
    assert v.cell_id == 1
    # Line 3 in local cell (import, df=..., df[...]...)
    assert v.lineno == 3
