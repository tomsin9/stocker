<script setup>
import { DialogDescription } from "reka-ui";
import { cn } from "@/lib/utils";

defineProps({
  class: { type: null, required: false },
});
</script>

<template>
  <DialogDescription :class="cn('text-sm text-muted-foreground', $props.class)">
    <slot />
  </DialogDescription>
</template>
