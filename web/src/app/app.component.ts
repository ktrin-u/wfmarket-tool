import { Component } from "@angular/core";
import { SearchBoxComponent } from "./search-box/search-box.component";

@Component({
    selector: "app-root",
    imports: [SearchBoxComponent],
    templateUrl: "./app.component.html",
    styleUrl: "./app.component.scss",
})
export class AppComponent {}
