"""Optional token-masking attribution; attention weights are not explanations."""
import torch
def explain(model, tokenizer, url, max_length=128, max_tokens=8):
    tokens = tokenizer(url, return_tensors="pt", truncation=True, max_length=max_length)
    model.eval()
    with torch.no_grad():
        baseline = float(torch.softmax(model(**tokens).logits, dim=1)[0,1])
        ids = tokens["input_ids"][0]
        candidates = [i for i, token in enumerate(ids.tolist()) if token not in tokenizer.all_special_ids][:max_tokens]
        observations = []
        for i in candidates:
            modified = {name: value.clone() for name,value in tokens.items()}
            modified["input_ids"][0,i] = tokenizer.mask_token_id
            p = float(torch.softmax(model(**modified).logits,dim=1)[0,1])
            observations.append({"token":tokenizer.convert_ids_to_tokens(int(ids[i])), "position":i, "probability_delta":baseline-p, "method":"single-token masking", "limitation":"bounded first tokens only; perturbation attribution, not proof of causality"})
    return observations
