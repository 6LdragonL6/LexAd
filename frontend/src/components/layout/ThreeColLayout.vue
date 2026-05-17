<template>
  <div class="flex flex-col lg:flex-row lg:gap-0 lg:h-full min-h-0">
    <aside class="w-full lg:w-72 shrink-0 overflow-y-auto border-b lg:border-b-0 lg:border-r border-gray-200 bg-gray-50 p-4">
      <slot name="left" />
    </aside>
    <main class="flex-1 overflow-y-auto p-4">
      <slot name="center" />
    </main>
    <aside class="w-full lg:w-96 shrink-0 overflow-y-auto border-t lg:border-t-0 lg:border-l border-gray-200 bg-gray-50 p-4">
      <slot name="right" />
    </aside>
  </div>
</template>
