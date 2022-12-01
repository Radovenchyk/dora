use dora_node_api::DoraNode;
use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    let mut node = DoraNode::init_from_env()?;
    let inputs = node.inputs()?;

    while let Ok(input) = inputs.recv() {
        match input.id.as_str() {
            other => eprintln!("Received input `{other}`"),
        }
    }

    Ok(())
}
