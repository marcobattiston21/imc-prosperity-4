import json
import sys

file_path = r"c:\Users\leona\imc-prosperity-4\prosperity4\round4\manual\Notebook_for_manual.ipynb"

with open(file_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

new_cell_source = """import matplotlib.pyplot as plt
import numpy as np
import sys, os
from contextlib import redirect_stdout

# Define tolerance values to test (log scale from 0.00001 to around 100)
tolerances = np.logspace(-5, 2, 20)
pnls = []
actual_deltas = []

print("Running optimization for various delta tolerances... This might take a few seconds.")

# We need the deltas dict to compute the actual delta
deltas = compute_all_deltas(instruments, paths)

for tol in tolerances:
    # redirect stdout to hide the print statements from solve_milp
    with open(os.devnull, 'w') as f, redirect_stdout(f):
        positions, model = solve_milp(instruments, paths, delta_neutral=True, delta_tolerance=tol)
        
    pnl = pulp.value(model.objective)
    
    # Recalculate actual net delta
    net_delta = sum(deltas[name] * q for name, q in positions.items())
    
    pnls.append(pnl)
    actual_deltas.append(abs(net_delta))

# Run one last time without delta neutrality constraint (delta_neutral=False)
with open(os.devnull, 'w') as f, redirect_stdout(f):
    positions_unconstrained, model_unconstrained = solve_milp(instruments, paths, delta_neutral=False)

unconstrained_pnl = pulp.value(model_unconstrained.objective)
unconstrained_delta = sum(deltas[name] * q for name, q in positions_unconstrained.items())

# Plotting
plt.figure(figsize=(10, 6))
# Plot the constrained points
plt.plot(actual_deltas, pnls, marker='o', linestyle='-', label='Delta Constrained', color='blue')

# Highlight the unconstrained point
plt.scatter([abs(unconstrained_delta)], [unconstrained_pnl], color='red', s=100, zorder=5, label='Unconstrained (delta_neutral=False)')

plt.title('Trade-off: Total Expected PnL vs Absolute Net Portfolio Delta')
plt.xlabel('Absolute Net Portfolio Delta')
plt.ylabel('Total Expected PnL (Edge)')
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.show()
"""

new_cell = {
    "cell_type": "code",
    "execution_count": None,
    "id": "tradeoff_plot",
    "metadata": {},
    "outputs": [],
    "source": [line + "\n" for line in new_cell_source.split('\n')[:-1]] + [new_cell_source.split('\n')[-1]]
}

# Remove the empty last cell if it exists, so we just append
if nb["cells"] and not nb["cells"][-1]["source"]:
    nb["cells"].pop()

nb["cells"].append(new_cell)

# Add a new empty cell at the end
nb["cells"].append({
    "cell_type": "code",
    "execution_count": None,
    "id": "empty_end",
    "metadata": {},
    "outputs": [],
    "source": []
})

with open(file_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)
    
print("Successfully appended plotting cell to Notebook_for_manual.ipynb")
