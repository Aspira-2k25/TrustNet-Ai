# Module roadmap

Image, scam message and phishing URL inference have runtime implementations. Their actual model roles and evaluation limitations are described in the module documentation.

Audio deepfake, video deepfake, fake review and OSINT remain design or future work. Empty Python packages and `.gitkeep` directory trees were removed from active source layout after checking that runtime imports do not depend on them. Their source scaffolding remains recoverable in the owner's external cleanup archive.

Future modules should be added when they have a concrete input contract, inference path, artifact distribution method, evaluation and failure-handling tests. Reserved enum values and architectural descriptions do not claim implemented or evaluated functionality.
