<script setup>
import { DialogTrigger } from "reka-ui";

defineProps({
  asChild: { type: Boolean, required: false },
});
</script>

<template>
  <DialogTrigger :as-child="asChild">
    <slot />
  </DialogTrigger>
</template>
