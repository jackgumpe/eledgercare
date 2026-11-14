import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'elc-root',
  imports: [RouterOutlet, RouterLink],
  template: `
    <main>
      <h1><a routerLink="/">eLedgerCare</a> · maintenance document intake</h1>
      <p class="note">Local development build. Synthetic documents only.</p>
      <router-outlet />
    </main>
  `,
})
export class App {}
