import yaml
import logging
from datasets import load_from_disk, concatenate_datasets
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
# We will create these modules in subsequent steps
# from rag import RagRetriever
# from sandbox import MockSandbox

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("training_debug.log"),
                        logging.StreamHandler()
                    ])

def main():
    logging.info("Starting training script...")
    # 1. Load Configuration
    logging.info("Loading configuration...")
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    logging.info("Configuration loaded successfully.")

    # 2. Load and Combine Datasets
    logging.info("Loading and combining datasets...")
    all_datasets = []
    for lang, path in config["datasets"].items():
        try:
            logging.info(f"Loading dataset for {lang} from {path}")
            dataset = load_from_disk(path)
            dataset = dataset.map(lambda example: {"language": lang})
            all_datasets.append(dataset)
            logging.info(f"Dataset for {lang} loaded successfully.")
        except FileNotFoundError:
            logging.warning(f"Dataset for {lang} not found at {path}. Skipping.")

    if not all_datasets:
        logging.error("No datasets found. Exiting.")
        return

    combined_dataset = concatenate_datasets(all_datasets)
    train_dataset = combined_dataset.select(range(100))
    eval_dataset = combined_dataset.select(range(100, 120))
    logging.info("Datasets combined and split successfully.")

    # 3. Initialize Tokenizer
    logging.info("Initializing tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["tokenizer_path"])
    tokenizer.add_special_tokens({"additional_special_tokens": config["model"]["special_tokens"]})
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    logging.info("Tokenizer initialized successfully.")

    def tokenize_function(examples):
        outputs = tokenizer(examples["code"], truncation=True, max_length=512)
        outputs["labels"] = outputs["input_ids"][:]
        return outputs

    logging.info("Tokenizing datasets...")
    tokenized_train_dataset = train_dataset.map(tokenize_function, batched=True)
    tokenized_eval_dataset = eval_dataset.map(tokenize_function, batched=True)
    logging.info("Datasets tokenized successfully.")

    # 4. Initialize Model
    logging.info("Initializing model...")
    model = AutoModelForCausalLM.from_pretrained(config["model"]["base_model"])
    model.resize_token_embeddings(len(tokenizer))
    logging.info("Model initialized successfully.")

    # 5. RAG Setup (Placeholder)
    logging.info("Skipping RAG setup (placeholder).")

    # 6. Training Arguments
    logging.info("Setting up training arguments...")
    training_args = TrainingArguments(
        output_dir=config["training"]["output_dir"],
        num_train_epochs=config["training"]["num_train_epochs"],
        per_device_train_batch_size=config["training"]["per_device_train_batch_size"],
        per_device_eval_batch_size=config["training"]["per_device_eval_batch_size"],
        gradient_accumulation_steps=config["training"]["gradient_accumulation_steps"],
        learning_rate=config["training"]["learning_rate"],
        weight_decay=config["training"]["weight_decay"],
        adam_beta1=config["training"]["adam_beta1"],
        adam_beta2=config["training"]["adam_beta2"],
        adam_epsilon=config["training"]["adam_epsilon"],
        max_grad_norm=config["training"]["max_grad_norm"],
        lr_scheduler_type=config["training"]["lr_scheduler_type"],
        warmup_steps=config["training"]["warmup_steps"],
        save_strategy=config["checkpointing"]["save_strategy"],
        save_total_limit=config["checkpointing"]["save_total_limit"],
        eval_strategy="epoch",
        logging_dir=f"{config['training']['output_dir']}/logs",
        logging_steps=config["logging"]["logging_steps"],
        report_to=config["logging"]["report_to"],
    )
    logging.info("Training arguments set up successfully.")

    # 7. Data Collator
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    # 8. Initialize Trainer
    logging.info("Initializing Trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_eval_dataset,
        data_collator=data_collator,
    )
    logging.info("Trainer initialized successfully.")

    # 9. Start Training
    logging.info("Starting training...")
    trainer.train()
    logging.info("Training completed.")

    # 10. Save Final Model and Reproducibility Log
    logging.info("Saving final model and reproducibility log...")
    trainer.save_model()
    with open(f"{config['training']['output_dir']}/reproducibility.log", "w") as f:
        f.write("Training completed successfully.\n")
        f.write(f"Config: {config}\n")
    logging.info("Model and log saved successfully.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical("An unhandled exception occurred: ", exc_info=True)
