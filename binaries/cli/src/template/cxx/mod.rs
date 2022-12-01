use eyre::{bail, Context};
use std::{
    fs,
    path::{Path, PathBuf},
};

pub fn create(args: crate::CommandNew) -> eyre::Result<()> {
    let crate::CommandNew {
        kind,
        lang: _,
        name,
        path,
    } = args;

    match kind {
        crate::Kind::Operator => create_operator(name, path),
        crate::Kind::CustomNode => create_custom_node(name, path),
        crate::Kind::Dataflow => create_dataflow(name, path),
    }
}

fn create_dataflow(name: String, path: Option<PathBuf>) -> Result<(), eyre::ErrReport> {
    const DATAFLOW_YML: &str = include_str!("dataflow-template.yml");

    if name.contains('/') {
        bail!("dataflow name must not contain `/` separators");
    }
    if !name.is_ascii() {
        bail!("dataflow name must be ASCII");
    }

    // create directories
    let root = path.as_deref().unwrap_or_else(|| Path::new(&name));
    fs::create_dir(root)
        .with_context(|| format!("failed to create directory `{}`", root.display()))?;

    let dataflow_yml = DATAFLOW_YML.replace("___name___", &name);
    let dataflow_yml_path = root.join("dataflow.yml");
    fs::write(&dataflow_yml_path, &dataflow_yml)
        .with_context(|| format!("failed to write `{}`", dataflow_yml_path.display()))?;

    create_operator("op_1".into(), Some(root.join("op_1")))?;
    create_operator("op_2".into(), Some(root.join("op_2")))?;
    create_custom_node("node_1".into(), Some(root.join("node_1")))?;

    println!(
        "Created new C++ dataflow at `{name}` at {}",
        Path::new(".").join(root).display()
    );

    Ok(())
}

fn create_operator(name: String, path: Option<PathBuf>) -> Result<(), eyre::ErrReport> {
    const OPERATOR: &str = include_str!("operator-template.cc");
    const HEADER: &str = include_str!("operator-template.h");

    if name.contains('/') {
        bail!("operator name must not contain `/` separators");
    }
    if !name.is_ascii() {
        bail!("operator name must be ASCII");
    }

    // create directories
    let root = path.as_deref().unwrap_or_else(|| Path::new(&name));
    fs::create_dir(root)
        .with_context(|| format!("failed to create directory `{}`", root.display()))?;

    let operator_path = root.join("operator.cc");
    fs::write(&operator_path, OPERATOR)
        .with_context(|| format!("failed to write `{}`", operator_path.display()))?;
    let header_path = root.join("operator.h");
    fs::write(&header_path, HEADER)
        .with_context(|| format!("failed to write `{}`", header_path.display()))?;

    // TODO: Makefile?

    println!(
        "Created new C++ operator `{name}` at {}",
        Path::new(".").join(root).display()
    );

    Ok(())
}

fn create_custom_node(name: String, path: Option<PathBuf>) -> Result<(), eyre::ErrReport> {
    const NODE: &str = include_str!("node-template.cc");

    if name.contains('/') {
        bail!("node name must not contain `/` separators");
    }
    if !name.is_ascii() {
        bail!("node name must be ASCII");
    }

    // create directories
    let root = path.as_deref().unwrap_or_else(|| Path::new(&name));
    fs::create_dir(root)
        .with_context(|| format!("failed to create directory `{}`", root.display()))?;

    let node_path = root.join("node.cc");
    fs::write(&node_path, NODE)
        .with_context(|| format!("failed to write `{}`", node_path.display()))?;

    // TODO: Makefile?

    println!(
        "Created new C++ custom node `{name}` at {}",
        Path::new(".").join(root).display()
    );

    Ok(())
}
