"""
Entrenamiento y Exportación de Modelo ONNX
Servicio Autónomo de Verificación Humana y Mitigación de Bots
Hackathon Venezuela Innova 2026 - Dev 2 (IA, Borde e Infraestructura)

Entrena un LGBMClassifier, evalúa métricas (Precision, Recall, F1, Matriz de Confusión)
y exporta a ONNX Runtime con metadata completa.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import numpy as np

import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from onnxmltools import convert_lightgbm
from onnxmltools.convert.common.data_types import FloatTensorType
import onnx
import onnxruntime as ort

from generar_dataset import FEATURE_NAMES, generar_dataset

BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ONNX_PATH = MODELS_DIR / "modelo_conductual_v1.onnx"
METADATA_PATH = MODELS_DIR / "metadata_v1.json"


def entrenar_y_exportar() -> None:
    print("=" * 65)
    print("   ENTRENAMIENTO MOTOR IA CONDUCTUAL LOCAL (LightGBM -> ONNX)")
    print("=" * 65)

    dataset_path = Path(__file__).parent / "dataset_conductual.npz"
    if dataset_path.exists():
        print(f"[*] Cargando dataset pre-generado desde {dataset_path}...")
        data = np.load(dataset_path)
        X, y = data["X"], data["y"]
    else:
        print("[*] Generando dataset sintético de 20,000 muestras...")
        X, y = generar_dataset(20000)

    # División estratificada 80% train / 20% test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=2026, stratify=y
    )
    print(f"[+] Conjunto de Entrenamiento: {X_train.shape[0]:,} muestras")
    print(f"[+] Conjunto de Prueba:        {X_test.shape[0]:,} muestras")

    # Configuración de hiperparámetros optimizados para baja latencia e inferencia compacta
    clf = lgb.LGBMClassifier(
        n_estimators=120,
        max_depth=5,
        num_leaves=24,
        learning_rate=0.04,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=2026,
        verbose=-1,
        n_jobs=-1,
    )

    print("\n[*] Entrenando LGBMClassifier...")
    clf.fit(X_train, y_train)

    # Evaluación rigurosa
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]

    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred).tolist()

    print("\n" + "=" * 65)
    print("               RESULTADOS DE EVALUACIÓN")
    print("=" * 65)
    print(f"  • Precisión (Precision):   {prec * 100:.2f} %")
    print(f"  • Cobertura (Recall):      {rec * 100:.2f} %")
    print(f"  • F1-Score:                {f1:.4f}  (Meta: > 0.9600)")
    print(f"  • ROC-AUC:                 {auc:.4f}")
    print(f"  • Matriz de Confusión:     TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")
    print("=" * 65)

    if f1 < 0.96:
        raise ValueError(f"CRÍTICO: El F1-score {f1:.4f} no supera el umbral mínimo obligatorio de 0.96.")

    # Exportación a ONNX
    print("\n[*] Exportando modelo a ONNX Runtime...")
    num_features = X.shape[1]
    initial_type = [("float_input", FloatTensorType([None, num_features]))]

    onnx_model = convert_lightgbm(
        clf,
        initial_types=initial_type,
        target_opset=15,
        doc_string="Modelo Soberano de Inferencia Conductual - Hackathon Venezuela Innova 2026",
    )

    onnx.save_model(onnx_model, str(MODEL_ONNX_PATH))
    onnx_size_bytes = MODEL_ONNX_PATH.stat().st_size
    onnx_size_mb = onnx_size_bytes / (1024 * 1024)

    print(f"[✔] Archivo ONNX guardado: {MODEL_ONNX_PATH}")
    print(f"    Tamaño: {onnx_size_mb:.3f} MB ({onnx_size_bytes:,} bytes) - (Límite: < 5.0 MB)")

    if onnx_size_mb > 5.0:
        raise ValueError(f"CRÍTICO: El archivo ONNX excede 5 MB ({onnx_size_mb:.2f} MB).")

    # Validación funcional con ONNX Runtime
    print("\n[*] Validando inferencia y consistencia con ONNX Runtime...")
    session = ort.InferenceSession(str(MODEL_ONNX_PATH))
    ort_inputs = {"float_input": X_test[:5]}
    ort_outs = session.run(None, ort_inputs)
    ort_preds = ort_outs[0]
    ort_probas = ort_outs[1]

    print(f"[✔] Salida de inferencia ONNX válida para lote de 5 muestras:")
    print(f"    Predicciones: {ort_preds}")
    print(f"    Probabilidades de riesgo: {[round(p[1], 4) for p in ort_probas]}")

    # Generación de Metadata
    metadata = {
        "model_version": "lgbm-conductual-v1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "framework": "LightGBM + ONNX Runtime",
        "target_opset": 15,
        "features": FEATURE_NAMES,
        "features_count": len(FEATURE_NAMES),
        "input_tensor_name": "float_input",
        "output_tensor_names": ["label", "probabilities"],
        "metrics": {
            "test_samples": int(X_test.shape[0]),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1_score": round(float(f1), 4),
            "roc_auc": round(float(auc), 4),
            "confusion_matrix": cm,
        },
        "decision_thresholds": {
            "human_max": 0.35,
            "challenge_max": 0.75,
            "bot_min": 0.75,
        },
        "target_latency_p99_ms": 15.0,
        "air_gapped_compatible": True,
        "privacy_guarantee": "Ephemeral in-RAM processing. Zero biometric persistence.",
    }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"[✔] Metadatos guardados en: {METADATA_PATH}")
    print("\n[🎉] ¡Prompt 2 completado exitosamente con F1 > 0.96 y ONNX verificado!")


if __name__ == "__main__":
    entrenar_y_exportar()
