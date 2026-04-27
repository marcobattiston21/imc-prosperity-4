import json
import sys

file_path = r"c:\Users\leona\imc-prosperity-4\prosperity4\round4\manual\Notebook_for_manual.ipynb"

with open(file_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        source = cell.get("source", [])
        for i, line in enumerate(source):
            if "def payoff(self, paths: np.ndarray) -> np.ndarray:\n" in line:
                if i + 3 < len(source) and "return paths[:, -1] - self.S0" in source[i+3]:
                    source[i+3] = source[i+3].replace("return paths[:, -1] - self.S0", "return paths[:, -1]")
                    print("Found and replaced!")

with open(file_path, "w", encoding="utf-8") as f:
    # use indent=1 to try and match the original formatting as close as possible
    # the original file seems to use indent=1
    json.dump(nb, f, indent=1)
