"""
snippets/05_model_hub_management.py — Model Hub Lifecycle Management

Demonstrates the full Model Hub workflow:
  1. Create a model repository (auto-creates v1.00)
  2. Create a new version
  3. Upload an ONNX model file
  4. List files in a version

The OpenGradient Model Hub is a decentralized model repository built on Walrus
(decentralized storage). All models uploaded here are instantly available for
inference on the OpenGradient network via og.Alpha.infer().

Model Format Requirements:
  - Models must be in ONNX format (.onnx)
  - ONNX is an open standard for ML models supported by PyTorch, TensorFlow,
    scikit-learn, and most other ML frameworks
  - Convert PyTorch: torch.onnx.export(model, dummy_input, "model.onnx")
  - Convert sklearn: from skl2onnx import convert_sklearn
  - For ZKML mode: additional size/complexity restrictions apply
    See: https://docs.opengradient.ai/models/model_hub/model_restrictions.html

Run:
    python snippets/05_model_hub_management.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from utils.client import get_hub, logger

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEMO_MODEL_NAME: str = "cookbook-demo-model"
DEMO_MODEL_DESC: str = "OpenGradient Cookbook demo model — volatility predictor"
DEMO_MODEL_NOTES: str = "Initial release — linear regression on OHLC features"
DEMO_ONNX_PATH: str = "model.onnx"   # Path to your ONNX file (must exist to upload)
DEMO_VERSION: str = "1.00"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def run_model_hub_demo() -> None:
    """Walk through the complete Model Hub lifecycle."""
    hub = get_hub()

    print("\n" + "=" * 60)
    print("🗂️  Model Hub Management Demo")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Create model repository
    # create_model() automatically creates version v1.00
    # ------------------------------------------------------------------
    print(f"\n📦 Step 1: Creating model repository '{DEMO_MODEL_NAME}'...")
    try:
        hub.create_model(
            model_name=DEMO_MODEL_NAME,
            model_desc=DEMO_MODEL_DESC,
        )
        print(f"✅ Model repository created: {DEMO_MODEL_NAME}")
        print(f"   Version v1.00 automatically initialized")
        print(f"   View at: https://hub.opengradient.ai/models/{DEMO_MODEL_NAME}")
    except Exception as e:
        # Model may already exist from a previous run — that's fine
        if "already exists" in str(e).lower() or "conflict" in str(e).lower():
            logger.warning(f"⚠️ Model '{DEMO_MODEL_NAME}' already exists — continuing...")
        else:
            logger.error(f"❌ Failed to create model: {e}")
            raise

    # ------------------------------------------------------------------
    # Step 2: Create a new version
    # Use versioning to track different iterations of your model
    # ------------------------------------------------------------------
    print(f"\n🔢 Step 2: Creating a new version...")
    try:
        new_version = hub.create_version(
            model_name=DEMO_MODEL_NAME,
            notes=DEMO_MODEL_NOTES,
        )
        print(f"✅ New version created: {new_version}")
    except Exception as e:
        logger.warning(f"⚠️ Could not create new version: {e}")
        new_version = DEMO_VERSION

    # ------------------------------------------------------------------
    # Step 3: Upload model file
    # The file must exist locally. We skip gracefully if it doesn't.
    # ------------------------------------------------------------------
    print(f"\n📤 Step 3: Uploading model file '{DEMO_ONNX_PATH}'...")
    if os.path.exists(DEMO_ONNX_PATH):
        try:
            hub.upload(
                model_path=DEMO_ONNX_PATH,
                model_name=DEMO_MODEL_NAME,
                version=DEMO_VERSION,
            )
            print(f"✅ Model uploaded successfully")
            print(f"   File: {DEMO_ONNX_PATH}")
            print(f"   Version: {DEMO_VERSION}")
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            raise
    else:
        print(f"⚠️ ONNX file not found at '{DEMO_ONNX_PATH}' — skipping upload")
        print(f"   To enable upload:")
        print(f"     1. Train a model and export to ONNX format")
        print(f"     2. Place it at: {os.path.abspath(DEMO_ONNX_PATH)}")
        print(f"   Quick example (scikit-learn → ONNX):")
        print(f"     from sklearn.linear_model import LinearRegression")
        print(f"     from skl2onnx import convert_sklearn")
        print(f"     model = LinearRegression().fit(X_train, y_train)")
        print(f"     onx = convert_sklearn(model, ...)")
        print(f"     with open('model.onnx', 'wb') as f: f.write(onx.SerializeToString())")

    # ------------------------------------------------------------------
    # Step 4: List files in a version
    # ------------------------------------------------------------------
    print(f"\n📋 Step 4: Listing files in version {DEMO_VERSION}...")
    try:
        files = hub.list_files(
            model_name=DEMO_MODEL_NAME,
            version=DEMO_VERSION,
        )
        if files:
            print(f"✅ Files in {DEMO_MODEL_NAME} v{DEMO_VERSION}:")
            for f in files:
                print(f"   • {f}")
        else:
            print(f"   (No files yet in version {DEMO_VERSION})")
    except Exception as e:
        logger.warning(f"⚠️ Could not list files: {e}")

    print("\n" + "=" * 60)
    print("✅ Model Hub demo complete!")
    print("=" * 60)
    print(
        "\nℹ️  Next step: use the model CID from the hub to run inference:\n"
        "   alpha = og.Alpha(private_key=os.getenv('OG_PRIVATE_KEY'))\n"
        "   result = alpha.infer(\n"
        "       model_cid='<your_model_cid_from_hub>',\n"
        "       model_input={'num_input1': [1.0, 2.0, 3.0]},\n"
        "       inference_mode=og.InferenceMode.VANILLA\n"
        "   )\n"
        "   See: snippets/08_ml_inference_alpha.py"
    )


if __name__ == "__main__":
    run_model_hub_demo()
