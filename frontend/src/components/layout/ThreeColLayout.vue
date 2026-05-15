<template>
  <div class="flex gap-0 h-full overflow-hidden">
    <aside class="w-280px shrink-0 overflow-y-auto border-r border-gray-200 bg-gray-50 p-4">
      <slot name="left" />
    </aside>
    <main class="flex-1 overflow-y-auto p-4">
      <slot name="center" />
    </main>
    <aside class="w-520px shrink-0 overflow-y-auto border-l border-gray-200 bg-gray-50 p-4">
      <slot name="right" />
    </aside>
  </div>
</template>
