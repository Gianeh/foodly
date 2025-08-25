# Foodly

Prototype di coach nutrizionale con interfaccia conversazionale.

## Limitazioni
- Parser rule-based con dizionario e pattern limitati; le frasi troppo complesse o con alimenti non noti possono non essere riconosciute.
- Tutte le quantità sono normalizzate in grammi; per i liquidi `ml` sono convertiti 1:1 in grammi.

## Fallback verso LLM
Quando il parser non è sufficiente o `use_rule_based=false`, l'applicazione delega la comprensione a un modello linguistico. È necessario fornire una chiave API (`FOODLY_API`) nelle impostazioni. Nel prototipo l'invocazione del modello non è ancora implementata.
