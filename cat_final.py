import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import SamplerV2
from qiskit.transpiler import generate_preset_pass_manager
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.widgets import Button
from qiskit.quantum_info import Statevector
import os
import json

THETA = 1.85

def prepare_statevector(angle):
    qc = QuantumCircuit(1)
    qc.rx(theta=angle,qubit=0)
    sv = Statevector(data=qc)
    return sv

def exact_probabilities(statevector):
    pr_0 = statevector[0] * np.conj(statevector[0])
    pr_1 = statevector[1] * np.conj(statevector[1])
    return pr_0, pr_1

sv = prepare_statevector(angle=THETA)
prob_0,prob_1 = exact_probabilities(statevector=sv)


class NumpyJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):  return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, (np.bool_,)):    return bool(obj)
        if isinstance(obj, complex):        return {"real": obj.real, "imag": obj.imag}
        return super().default(obj)


filename = "results_friday.json"
# filename = "results_saturday.json"
# filename = "results_sunday.json"



script_dir = os.path.dirname(os.path.abspath(__file__))
chest_path = os.path.join(script_dir, "chest.png")
happy_path = os.path.join(script_dir, "happy.png")
grumpy_path = os.path.join(script_dir, "grumpy.png")

file_path = os.path.join(script_dir, filename)

try:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data = {"alive_count": 0, "dead_count": 0}

img_chest = mpimg.imread(chest_path)
img_happy = mpimg.imread(happy_path)
img_grumpy = mpimg.imread(grumpy_path)


def generate_circuit(theta):
    qc = QuantumCircuit(1)
    qc.rx(theta, 0)
    return qc


fig, (ax_img, ax_hist) = plt.subplots(1, 2, figsize=(12, 6))
fig.canvas.manager.set_window_title("Schrödinger's Cat Experiment")
plt.subplots_adjust(bottom=0.22)  

app_state = {
    "phase": "CHEST", 
    "current_cat_img": None
}


prob_text = fig.text(
    0.5, 0.12, 
    "", 
    ha='center', va='center', fontsize=14, style='italic', color='#333333'
)

def update_dashboard():
    """Clears and redraws the images and histogram based on current state."""
    ax_img.clear()
    ax_hist.clear()

    if app_state["phase"] == "CHEST":
        ax_img.imshow(img_chest)
        ax_img.set_title("Pro otevření klikněte na krabici!", fontsize=16, pad=10)
    else:
        ax_img.imshow(app_state["current_cat_img"])
        ax_img.set_title(f"Klikněte kamkoliv pro další měření.", fontsize=16, pad=10)
    ax_img.axis("off")

    labels = ['Šťastná', 'Smutná']
    counts = [data.get("alive_count", 0), data.get("dead_count", 0)]
    
    bars = ax_hist.bar(labels, counts, color=['#4CAF50', '#757575'])
    today_total = data.get("alive_count", 0) + data.get("dead_count", 0)
    ax_hist.set_title(f"Dnes návštěvníků celkem: {today_total}", fontsize=16, pad=10)
    ax_hist.set_ylabel("Počet", fontsize=12)
    
    max_count = max(counts) if max(counts) > 0 else 5
    ax_hist.set_ylim(0, max_count * 1.15)

    for bar in bars:
        yval = bar.get_height()
        ax_hist.text(bar.get_x() + bar.get_width()/2.0, yval + (max_count * 0.02), 
                     int(yval), ha='center', va='bottom', fontsize=14, fontweight='bold')

    #dynamic probability
    if today_total == 0:
        value = 0.0
    else:
        value = data.get("alive_count", 0) / today_total

    prob_text.set_text(f"Pr(Šťastná kočka) = {value:.4f}\n Exaktní = {prob_1.real:.4f}")
    
    fig.canvas.draw_idle()


def on_click(event):
    """Handles clicks on the image side of the dashboard."""
    if event.inaxes == ax_img:
        
        if app_state["phase"] == "CHEST":
            qc = generate_circuit(THETA)
            qc.measure_all()
            
            fake_backend = AerSimulator()
            pm = generate_preset_pass_manager(optimization_level=1, backend=fake_backend)
            isa_circuit = pm.run(qc)

            sampler = SamplerV2(mode=fake_backend)
            job = sampler.run([isa_circuit], shots=1)
            result = job.result()[0]
            counts = result.data.meas.get_counts()

            if list(counts.keys())[0] == "0":
                print('Result: Cat is dead')
                data["dead_count"] = data.get("dead_count", 0) + 1
                app_state["current_cat_img"] = img_grumpy
            else:
                print('Result: Cat is alive')
                data["alive_count"] = data.get("alive_count", 0) + 1
                app_state["current_cat_img"] = img_happy

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False, cls=NumpyJSONEncoder)

            app_state["phase"] = "RESULT"
            update_dashboard()

        elif app_state["phase"] == "RESULT":
            app_state["phase"] = "CHEST"
            update_dashboard()

fig.canvas.mpl_connect('button_press_event', on_click)

btn_ax = fig.add_axes([0.45, 0.03, 0.1, 0.05])  
btn_cancel = Button(btn_ax, "Exit", color='lightcoral', hovercolor='red')

def on_cancel_click(event):
    plt.close(fig)

btn_cancel.on_clicked(on_cancel_click)

update_dashboard()

plt.show() 
print("Program exited gracefully.")
