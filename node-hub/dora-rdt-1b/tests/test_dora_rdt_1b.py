import pytest


def test_import_main():
    # from dora_rdt_1b.main import main

    # Check that everything is working, and catch dora Runtime Exception as we're not running in a dora dataflow.
    # with pytest.raises(RuntimeError):
    pass
    # main()
    import dora_rdt_1b
    import dora_rdt_1b.RoboticsDiffusionTransformer


def test_dummy_input():
    # install dependencies as shown in the README here https://github.com/alik-git/RoboticsDiffusionTransformer?tab=readme-ov-file#installation
    import yaml
    import torch
    import numpy as np
    from PIL import Image
    from torchvision import transforms

    from dora_rdt_1b.RoboticsDiffusionTransformer.configs.state_vec import (
        STATE_VEC_IDX_MAPPING,
    )
    from dora_rdt_1b.RoboticsDiffusionTransformer.models.multimodal_encoder.siglip_encoder import (
        SiglipVisionTower,
    )
    from dora_rdt_1b.RoboticsDiffusionTransformer.models.rdt_runner import RDTRunner

    # other imports

    config_path = "/home/peter/Documents/work/dora/node-hub/dora-rdt-1b/dora_rdt_1b/RoboticsDiffusionTransformer/configs/base.yaml"  # default config
    pretrained_model_name_or_path = "robotics-diffusion-transformer/rdt-1b"
    device = torch.device("cuda:0")
    dtype = torch.bfloat16  # recommanded
    cfg_scale = 2.0

    # suppose you control in 7DOF joint position
    STATE_INDICES = [
        STATE_VEC_IDX_MAPPING["arm_joint_0_pos"],
        STATE_VEC_IDX_MAPPING["arm_joint_1_pos"],
        STATE_VEC_IDX_MAPPING["arm_joint_2_pos"],
        STATE_VEC_IDX_MAPPING["arm_joint_3_pos"],
        STATE_VEC_IDX_MAPPING["arm_joint_4_pos"],
        STATE_VEC_IDX_MAPPING["arm_joint_5_pos"],
        STATE_VEC_IDX_MAPPING["arm_joint_6_pos"],
        STATE_VEC_IDX_MAPPING["gripper_open"],
    ]

    with open(config_path, "r") as fp:
        config = yaml.safe_load(fp)

    # Load vision encoder
    vision_encoder = SiglipVisionTower(
        vision_tower="google/siglip-so400m-patch14-384", args=None
    )
    vision_encoder.to(device, dtype=dtype)
    vision_encoder.eval()
    image_processor = vision_encoder.image_processor

    # Load pretrained model (in HF style)
    rdt = RDTRunner.from_pretrained(pretrained_model_name_or_path)
    rdt.to(device, dtype=dtype)
    rdt.eval()

    # Load language embeddings # this part I belive can be done via the `encode_lang.py` script, which I have managed to do
    lang_embeddings = torch.load("path/to/outs/handover_pan.pt", map_location=device)

    # -------------------------------------

    previous_image_path = "/home/peter/Documents/work/dora/output.jpg"
    # previous_image = None # if t = 0
    previous_image = Image.open(previous_image_path).convert("RGB")  # if t > 0

    current_image_path = "/home/peter/Documents/work/dora/output.jpg"
    current_image = Image.open(current_image_path).convert("RGB")

    # here I suppose you only have an image from exterior (e.g., 3rd person view) and you don't have any state information
    # the images shoud arrange in sequence [exterior_image, right_wrist_image, left_wrist_image] * image_history_size (e.g., 2)
    rgbs_lst = [[previous_image, None, None], [current_image, None, None]]
    # if your have an right_wrist_image, then it should be
    # rgbs_lst = [
    #     [previous_image, previous_right_wrist_image, None],
    #     [current_image, current_right_wrist_image, None]
    # ]

    # image pre-processing
    # The background image used for padding
    background_color = np.array(
        [int(x * 255) for x in image_processor.image_mean], dtype=np.uint8
    ).reshape(1, 1, 3)
    background_image = (
        np.ones(
            (image_processor.size["height"], image_processor.size["width"], 3),
            dtype=np.uint8,
        )
        * background_color
    )

    image_tensor_list = []
    for step in range(config["common"]["img_history_size"]):
        rgbs = rgbs_lst[step % len(rgbs_lst)]
        for rgb in rgbs:
            if rgb is None:
                # Replace it with the background image
                image = Image.fromarray(background_image)
            else:
                image = Image.fromarray((rgb * 255).astype(np.uint8))

            if config["dataset"].get("auto_adjust_image_brightness", False):
                pixel_values = list(image.getdata())
                average_brightness = sum(sum(pixel) for pixel in pixel_values) / (
                    len(pixel_values) * 255.0 * 3
                )
                if average_brightness <= 0.15:
                    image = transforms.ColorJitter(brightness=(1.75, 1.75))(image)

            if config["dataset"].get("image_aspect_ratio", "pad") == "pad":

                def expand2square(pil_img, background_color):
                    width, height = pil_img.size
                    if width == height:
                        return pil_img
                    elif width > height:
                        result = Image.new(
                            pil_img.mode, (width, width), background_color
                        )
                        result.paste(pil_img, (0, (width - height) // 2))
                        return result
                    else:
                        result = Image.new(
                            pil_img.mode, (height, height), background_color
                        )
                        result.paste(pil_img, ((height - width) // 2, 0))
                        return result

                image = expand2square(
                    image, tuple(int(x * 255) for x in image_processor.image_mean)
                )
            image = image_processor.preprocess(image, return_tensors="pt")[
                "pixel_values"
            ][0]
            image_tensor_list.append(image)

    image_tensor = torch.stack(image_tensor_list, dim=0).to(device, dtype=dtype)

    # encode images
    image_embeds = vision_encoder(image_tensor).detach()
    image_embeds = image_embeds.reshape(-1, vision_encoder.hidden_size).unsqueeze(0)

    # suppose you do not have proprio
    # it's kind of tricky, I strongly suggest adding proprio as input and futher fine-tuning
    B, N = 1, 1  # batch size and state history size
    states = torch.zeros(
        (B, N, config["model"]["state_token_dim"]), device=device, dtype=dtype
    )

    # if you have proprio, you can do like this
    # format like this: [arm_joint_0_pos, arm_joint_1_pos, arm_joint_2_pos, arm_joint_3_pos, arm_joint_4_pos, arm_joint_5_pos, arm_joint_6_pos, gripper_open]
    # proprio = torch.tensor([0, 1, 2, 3, 4, 5, 6, 0.5]).reshape((1, 1, -1))
    # states[:, :, STATE_INDICES] = proprio

    state_elem_mask = torch.zeros(
        (B, config["model"]["state_token_dim"]), device=device, dtype=torch.bool
    )
    state_elem_mask[:, STATE_INDICES] = True
    states, state_elem_mask = states.to(device, dtype=dtype), state_elem_mask.to(
        device, dtype=dtype
    )
    states = states[:, -1:, :]  # only use the last state

    actions = rdt.predict_action(
        lang_tokens=lang_embeddings.to(device, dtype=dtype),
        lang_attn_mask=torch.ones(
            lang_embeddings.shape[:2], dtype=torch.bool, device=device
        ),
        img_tokens=image_embeds,
        state_tokens=states,  # how can I get this?
        action_mask=state_elem_mask.unsqueeze(1),  # how can I get this?
        ctrl_freqs=torch.tensor([25.0], device=device),  # would this default work?
    )  # (1, chunk_size, 128)

    # select the meaning action via STATE_INDICES
    action = actions[
        :, :, STATE_INDICES
    ]  # (1, chunk_size, len(STATE_INDICES)) = (1, chunk_size, 7+ 1)
