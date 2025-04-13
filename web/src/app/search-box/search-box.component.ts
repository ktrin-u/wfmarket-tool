import { Component } from "@angular/core";
import { ApiService } from "../api.service";
import { inject } from "@angular/core";
import { Result } from "../models/search-results";

@Component({
    selector: "app-search-box",
    imports: [],
    templateUrl: "./search-box.component.html",
    styleUrl: "./search-box.component.scss",
    providers: [ApiService],
})
export class SearchBoxComponent {
    apiService = inject(ApiService)
    query_results = "";
    placeholder = "Item Name";

    getFloorPrice(item_name: string) {
        let ret = this.apiService.getFloorPrice(item_name).subscribe(result => {
            let prices = result.body?.prices
            if ( prices?.length != 0 ){
                this.query_results = String(result.body?.prices)
                return
            }
            this.query_results = "Invalid item"
        });
    }
}
