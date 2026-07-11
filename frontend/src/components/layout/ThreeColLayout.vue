<template>
  <div class="three-col">
    <aside class="three-col-left">
      <slot name="left" />
    </aside>
    <main class="three-col-center">
      <slot name="center" />
    </main>
    <aside class="three-col-right">
      <slot name="right" />
    </aside>
  </div>
</template>
