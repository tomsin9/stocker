<script setup>
import { DialogTitle } from "reka-ui";
import { cn } from "@/lib/utils";

defineProps({
  class: { type: null, required: false },
});
</script>

<template>
  <DialogTitle :class="cn('text-lg font-semibold text-foreground', $props.class)">
    <slot />
  </DialogTitle>
</template>
