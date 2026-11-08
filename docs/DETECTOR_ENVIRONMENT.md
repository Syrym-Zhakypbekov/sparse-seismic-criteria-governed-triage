# Detector environment (secondary analyses, Section 4.5)

| Item | Value |
|---|---|
| SeisBench | 0.12.7 (local environment, 07.11.2026); Kaggle, Colab and the Google Cloud VM installed SeisBench from PyPI on 07.11.2026 |
| PyTorch | 2.15.0+cpu (laptop); GPU build on Colab |
| ObsPy | 1.5.1 |
| EQTransformer weights | "original", weights version 3; original.pt.v3 SHA-256 prefix c363c59dfb4562ba (1,597,711 bytes); original.json.v3 e499eeee66e3e86e |
| PhaseNet weights | "instance", weights version 2; instance.pt.v2 SHA-256 prefix dddcc3d872106a8c (1,112,615 bytes); instance.json.v2 d0f33eb054818b6e |
| Prediction tables | results/eqt/eqt_episodes.csv (EQTransformer, 1394 episodes), results/phasenet/phasenet_episodes.csv (PhaseNet, 1394 episodes), results/eqt_vm_cpu/ (CPU cross-check, 3000 extended episodes) |
| Channel sampling rates | IU.MAKZ.00.BHZ 40 Hz, IM.MK31..BHZ 40 Hz, II.KURK.00.BHZ 40 Hz, G.WUS.00.BHZ 20 Hz (EarthScope station metadata 2024–2026) |
