"""Helpers for YAML-defined mirrors of QEC-Compiler benchmark examples.

The public definitions live in ``pyqres/dsl/schemas/composites/qec_examples.yml``.
These helpers keep generated YAML classes small while preserving exact
gate-level parity with QEC-Compiler's benchmark builders.
"""

from __future__ import annotations

import math
from math import gcd

from ..core.registry import OperationRegistry


def append_qec_gate(program_list, qreg: str, name: str, qubits, params=()) -> None:
    gate_cls = OperationRegistry.get_class("QECGate")
    program_list.append(
        gate_cls(reg_list=[qreg], param_list=[name, list(qubits), list(params)])
    )


def build_qec_ghz(program_list, qreg: str, n: int) -> None:
    append_qec_gate(program_list, qreg, "H", (0,))
    for i in range(n - 1):
        append_qec_gate(program_list, qreg, "CNOT", (i, i + 1))


def build_qec_w(program_list, qreg: str, n: int) -> None:
    def rec(i: int) -> None:
        if i == n - 1:
            append_qec_gate(program_list, qreg, "X", (i,))
            return
        theta = 2 * math.asin(math.sqrt((n - i - 1) / (n - i)))
        append_qec_gate(program_list, qreg, "RY", (i,), (theta,))
        append_qec_gate(program_list, qreg, "CNOT", (i, i + 1))
        append_qec_gate(program_list, qreg, "RY", (i + 1,), (-theta,))
        append_qec_gate(program_list, qreg, "CNOT", (i, i + 1))
        append_qec_gate(program_list, qreg, "X", (i,))
        rec(i + 1)

    rec(0)


def build_qec_bv(program_list, qreg: str, n: int, secret: int) -> None:
    for i in range(n):
        append_qec_gate(program_list, qreg, "H", (i,))
    for i in range(n):
        if (secret >> i) & 1:
            append_qec_gate(program_list, qreg, "CNOT", (i, n))
    for i in range(n):
        append_qec_gate(program_list, qreg, "H", (i,))


def build_qec_dj(program_list, qreg: str, n: int, balanced: bool) -> None:
    ancilla = n
    append_qec_gate(program_list, qreg, "X", (ancilla,))
    append_qec_gate(program_list, qreg, "H", (ancilla,))
    for i in range(n):
        append_qec_gate(program_list, qreg, "H", (i,))
    if balanced:
        for i in range(n):
            append_qec_gate(program_list, qreg, "CNOT", (i, ancilla))
    for i in range(n):
        append_qec_gate(program_list, qreg, "H", (i,))


def build_qec_grover(program_list, qreg: str, n: int, marked_states, iterations: int) -> None:
    for i in range(n):
        append_qec_gate(program_list, qreg, "H", (i,))
    for _ in range(iterations):
        for target in marked_states:
            for i in range(n):
                if (int(target) >> i) & 1:
                    append_qec_gate(program_list, qreg, "X", (i,))
        for i in range(n - 1):
            append_qec_gate(program_list, qreg, "CNOT", (i, i + 1))
        append_qec_gate(program_list, qreg, "X", (n - 1,))
        for i in range(n):
            append_qec_gate(program_list, qreg, "X", (i,))
        for i in range(n):
            append_qec_gate(program_list, qreg, "H", (i,))


def build_qec_qft(program_list, qreg: str, n: int) -> None:
    for i in range(n):
        append_qec_gate(program_list, qreg, "H", (i,))
        for j in range(i + 1, n):
            theta = math.pi / (1 << (j - i))
            append_qec_gate(program_list, qreg, "CPHASE", (i, j), (theta,))
    for i in range(n // 2):
        append_qec_gate(program_list, qreg, "SWAP", (i, n - 1 - i))


def _append_iqft(program_list, qreg: str, n: int) -> None:
    for i in range(n // 2):
        append_qec_gate(program_list, qreg, "SWAP", (i, n - 1 - i))
    for i in reversed(range(n)):
        for j in reversed(range(i + 1, n)):
            theta = -math.pi / (1 << (j - i))
            append_qec_gate(program_list, qreg, "CPHASE", (i, j), (theta,))
        append_qec_gate(program_list, qreg, "H", (i,))


def build_qec_qpe(
    program_list,
    qreg: str,
    n_counting: int,
    n_system: int,
    unitary_eigenvalue: float,
) -> None:
    for i in range(n_counting):
        append_qec_gate(program_list, qreg, "H", (i,))
    phase = 2 * math.pi * unitary_eigenvalue
    for i in range(n_counting):
        theta = phase * (1 << i)
        for s in range(n_system):
            append_qec_gate(program_list, qreg, "CPHASE", (i, n_counting + s), (theta,))
    _append_iqft(program_list, qreg, n_counting)


def build_qec_qaoa(
    program_list,
    qreg: str,
    n_vertices: int,
    edges,
    p: int,
    gamma: float,
    beta: float,
) -> None:
    for i in range(n_vertices):
        append_qec_gate(program_list, qreg, "H", (i,))
    for _layer in range(p):
        g = gamma / p
        b = beta / p
        for u, v in edges:
            append_qec_gate(program_list, qreg, "CNOT", (u, v))
            append_qec_gate(program_list, qreg, "RZ", (v,), (g,))
            append_qec_gate(program_list, qreg, "CNOT", (u, v))
        for i in range(n_vertices):
            append_qec_gate(program_list, qreg, "RX", (i,), (b,))


def build_qec_vqe(
    program_list,
    qreg: str,
    n_qubits: int,
    layers: int,
    ring_entanglement: bool,
) -> None:
    for layer in range(layers):
        scale = layer + 1
        for qubit in range(n_qubits):
            theta_y = math.pi * scale * (qubit + 1) / (2 * (n_qubits + layers))
            theta_z = math.pi * scale * (qubit + 2) / (4 * (n_qubits + layers))
            append_qec_gate(program_list, qreg, "RY", (qubit,), (theta_y,))
            append_qec_gate(program_list, qreg, "RZ", (qubit,), (theta_z,))
        for control in range(n_qubits - 1):
            append_qec_gate(program_list, qreg, "CNOT", (control, control + 1))
        if ring_entanglement and n_qubits > 2:
            append_qec_gate(program_list, qreg, "CNOT", (n_qubits - 1, 0))


def build_qec_ising(
    program_list,
    qreg: str,
    n_spins: int,
    couplings,
    p_level: int,
    h_transverse: float,
) -> None:
    dt = 0.1
    for _ in range(p_level):
        for i, coupling in enumerate(couplings):
            append_qec_gate(program_list, qreg, "CNOT", (i, i + 1))
            append_qec_gate(program_list, qreg, "RZ", (i + 1,), (-float(coupling) * dt,))
            append_qec_gate(program_list, qreg, "CNOT", (i, i + 1))
        for i in range(n_spins):
            append_qec_gate(program_list, qreg, "RX", (i,), (-h_transverse * dt,))


def build_qec_swap_test(program_list, qreg: str, total_qubits: int) -> None:
    n_data = (total_qubits - 1) // 2
    ancilla = 0
    left_register = tuple(range(1, 1 + n_data))
    right_register = tuple(range(1 + n_data, total_qubits))
    append_qec_gate(program_list, qreg, "H", (ancilla,))
    for offset, qubit in enumerate(left_register):
        angle = math.pi * (offset + 1) / (2 * (n_data + 1))
        append_qec_gate(program_list, qreg, "RY", (qubit,), (angle,))
    for offset, qubit in enumerate(right_register):
        angle = math.pi * (offset + 2) / (3 * (n_data + 1))
        append_qec_gate(program_list, qreg, "RZ", (qubit,), (angle,))
        if offset % 2 == 0:
            append_qec_gate(program_list, qreg, "X", (qubit,))
    for left, right in zip(left_register, right_register, strict=True):
        append_qec_gate(program_list, qreg, "CNOT", (right, left))
        append_qec_gate(program_list, qreg, "CCX", (ancilla, left, right))
        append_qec_gate(program_list, qreg, "CNOT", (right, left))
    append_qec_gate(program_list, qreg, "H", (ancilla,))


def build_qec_small_shor(program_list, qreg: str, modulus: int, base: int) -> None:
    if gcd(base, modulus) != 1:
        raise ValueError("base must be coprime with modulus")
    if modulus == 15:
        counting_bits, work_bits = 4, 4
    elif modulus == 21:
        counting_bits, work_bits = 6, 5
    else:
        raise ValueError("small Shor YAML mirror supports only N=15 and N=21")

    work_register = tuple(range(counting_bits, counting_bits + work_bits))
    append_qec_gate(program_list, qreg, "X", (work_register[0],))
    for qubit in range(counting_bits):
        append_qec_gate(program_list, qreg, "H", (qubit,))

    multiplier = base % modulus
    for control in range(counting_bits):
        append_qec_gate(
            program_list,
            qreg,
            "CMUL_MOD_N",
            (control, *work_register),
            (float(multiplier), float(modulus)),
        )
        multiplier = pow(multiplier, 2, modulus)

    for left, right in zip(
        range(counting_bits // 2),
        reversed(range((counting_bits + 1) // 2, counting_bits)),
        strict=False,
    ):
        append_qec_gate(program_list, qreg, "SWAP", (left, right))
    for target_offset, target in enumerate(range(counting_bits)):
        for control_offset, control in enumerate(range(target_offset)):
            angle = -math.pi / (1 << (target_offset - control_offset))
            append_qec_gate(program_list, qreg, "CPHASE", (control, target), (angle,))
        append_qec_gate(program_list, qreg, "H", (target,))
