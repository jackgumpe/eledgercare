import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'elc-root',
  imports: [RouterOutlet, RouterLink],
  template: `
    <main>
      <div class="app-header-row">
        <h1><a routerLink="/">eLedgerCare</a> · maintenance document intake</h1>
        <nav aria-label="Primary navigation" class="app-nav">
          <a routerLink="/" data-testid="nav-intake">Intake</a>
          ·
          <a routerLink="/archive" data-testid="nav-archive">Archive search</a>
        </nav>
      </div>
      <p class="note">Local development build. Synthetic documents only.</p>
      <router-outlet />
    </main>
  `,
})
export class App {}
