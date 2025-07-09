"use client";

import { useState, useEffect } from "react";
import { jsPDF } from "jspdf";
import "jspdf-autotable";
import useFetch from "@/hooks/useFetch";
import { toast } from "sonner";
import CustomButton from "@/components/theme/customButton";
import SearchBar from "@/admin_components/common/searchBar";
import Pagination from "@/admin_components/common/pagination";
import { PuffLoader } from "react-spinners";
import { CloudArrowDownIcon } from "@/admin_components/icons";

const numberWithCommas = (value: number | string) => {
  if (value === undefined || value === null) return "0";
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

const TradeAnalysis = () => {
  const [searchValue, setSearchValue] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsOnPage = 10;

  const [getTradeAnalysis, { response, loading, error }] = useFetch(
    "/admin/dashboard/",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  useEffect(() => {
    getTradeAnalysis({
      body: JSON.stringify({ percentageUp: 5, percentageDown: 5 }), 
    });
  }, []);

  useEffect(() => {
    if (error) {
      toast.error(error?.message);
    }
  }, [error]);

  console.log("DEBUG: API Response", response?.data); 

  const tradeData = response?.data?.portfolio_premiums || [];

  const filteredTrades = tradeData
    .filter((trade) =>
      searchValue ? trade.account_id?.toString().includes(searchValue) : true
    )
    .sort((a, b) => Number(a.account_id) - Number(b.account_id));

  const paginatedTrades = filteredTrades.slice(
    (currentPage - 1) * itemsOnPage,
    currentPage * itemsOnPage
  );

  const totalRecords = filteredTrades.length;
  const totalPages = Math.ceil(totalRecords / itemsOnPage);

  const handlePageChange = (pageNumber: number) => {
    setCurrentPage(pageNumber);
  };

  const handleDownloadPDF = () => {
    const input = document.getElementById("tradeAnalysisTable");
    if (!input) return;
  
    const pdf = new jsPDF("l", "mm", "a4");
    const pageWidth = pdf.internal.pageSize.getWidth();
  
    pdf.setFont("times", "normal");

    const logo = "/assets/image/logo.png";
    const imgWidth = 50;
    const imgHeight = 50;
    const xPositionLogo = (pageWidth - imgWidth) / 2;
    pdf.addImage(logo, "PNG", xPositionLogo, 50, imgWidth, imgHeight);
  
    pdf.setFontSize(20);
    pdf.setFont("times", "bold");
    pdf.text("Trade Analysis Report", pageWidth / 2, 120, { align: "center" });
    const currentDate = new Date().toLocaleDateString();
    pdf.setFontSize(14);
    pdf.text(`Generated on: ${currentDate}`, pageWidth / 2, 140, { align: "center" });
  
    pdf.addPage();
  
    const rows = Array.from(input.getElementsByTagName("tr"));
    const headers = rows[0].getElementsByTagName("th");
    const headersArray = Array.from(headers).map(header => header.innerText.trim());
    const data = rows.slice(1).map(row =>
      Array.from(row.getElementsByTagName("td")).map(cell => cell.innerText.trim())
    );
  
    const generalTradeColumns = [0, 1, 2, 3, 4, 5, 6, 7];
    const profitLossColumns = [0, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19];
  
    const extractColumns = (columns: number[]) => {
      const newHeaders = columns.map(index => headersArray[index]);
      const newData = data.map(row => columns.map(index => row[index]));
      return { newHeaders, newData };
    };
  
    const { newHeaders: generalHeaders, newData: generalData } = extractColumns(generalTradeColumns);
    const { newHeaders: profitHeaders, newData: profitData } = extractColumns(profitLossColumns);
  
    let startY = 20;
    pdf.setFontSize(10);
    pdf.text("General Trade Metrics", pageWidth / 2, startY, { align: "center" });
  
    pdf.autoTable({
      head: [generalHeaders],
      body: generalData,
      startY: startY + 10,
      theme: "grid",
      styles: { fontSize: 10, cellPadding: 3, font: "times" },
      headStyles: { fillColor: [0, 0, 0], textColor: [255, 255, 255], fontStyle: "bold" },
      bodyStyles: { textColor: [0, 0, 0], font: "times" },
      alternateRowStyles: { fillColor: [230, 230, 255] },
    });
  
    const tableHeight = pdf.lastAutoTable.finalY + 10;
    pdf.setFontSize(10);
    pdf.text("Profit & Loss Metrics", pageWidth / 2, tableHeight, { align: "center" });
  
    pdf.autoTable({
      head: [profitHeaders],
      body: profitData,
      startY: tableHeight + 10,
      theme: "grid",
      styles: { fontSize: 10, cellPadding: 3, font: "times" },
      headStyles: { fillColor: [0, 0, 0], textColor: [255, 255, 255], fontStyle: "bold" },
      bodyStyles: { textColor: [0, 0, 0], font: "times" },
      alternateRowStyles: { fillColor: [230, 230, 255] },
    });
  
    const totalPages = pdf.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      pdf.setPage(i);
      pdf.setFontSize(10);
      pdf.text(`Page ${i} of ${totalPages}`, pageWidth - 20, pdf.internal.pageSize.getHeight() - 10);
    }
  
    pdf.save("trade_analysis.pdf");
  };

  return (
    <div className="ring-1 ring-borderColor bg-white p-4 md:p-7 pb-[10px] md:pb-[10px] rounded-[10px] min-h-[50vh]">
      <div className="flex justify-between items-center mb-8 gap-5">
        <div className="basis-[100%] md:basis-[33.33%]">
          <SearchBar
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="Search by Account ID"
          />
        </div>

        <div>
          <CustomButton
            variantType="filled"
            rightIcon={<CloudArrowDownIcon />}
            onClick={handleDownloadPDF}
          >
            Download as PDF
          </CustomButton>
        </div>
      </div>

      <div className="theme-table">
        <table id="tradeAnalysisTable">
          <thead className="sticky top-0 z-20">
            <tr>
              <th scope="col">Account ID</th>
              <th scope="col">Starting Period</th>
              <th scope="col">Ending Period</th>
              <th scope="col">Total Accumulated Premiums</th>
              <th scope="col">Total Contracts Sold</th>
              <th scope="col">Total Expired Calls</th>
              <th scope="col">Premiums From Expired Calls</th>
              <th scope="col">Total Expired Puts</th>
              <th scope="col">Premiums From Expired Puts</th>
              <th scope="col">Total Premiums From Expired Contracts</th>
              <th scope="col">Total Bought Back Calls</th>
              <th scope="col">P&L From Bought Back Calls</th>
              <th scope="col">Total Bought Back Puts</th>
              <th scope="col">P&L From Bought Back Puts</th>
              <th scope="col">Total P&L From Bought Back Contracts</th>
              <th scope="col">Total Assigned Calls</th>
              <th scope="col">Realized P&L From Assigned Calls</th>
              <th scope="col">Total Assigned Puts</th>
              <th scope="col">MTM P&L From Assigned Puts</th>
              <th scope="col">Total P&L From Assigned Contracts</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={18}>
                  <div className="w-full min-h-[300px] flex items-center justify-center">
                    <PuffLoader color="#ff782c" />
                  </div>
                </td>
              </tr>
            )}
            {!loading &&
              paginatedTrades.map((trade) => (
                <tr key={trade.account_id}>
                  <td>{trade.account_id}</td>
                  <td>{trade.first_date}</td>
                  <td>{trade.last_date}</td>
                  <td>${numberWithCommas(Number(trade.total_premiums?.toFixed(2) || 0))}</td>
                  <td>{trade.total_contracts_sold}</td>
                  <td>{trade.expired_calls}</td>
                  <td>${numberWithCommas(Number(trade.expired_call_premiums?.toFixed(2) || 0))}</td>
                  <td>{trade.expired_puts}</td>
                  <td>${numberWithCommas(Number(trade.expired_put_premiums?.toFixed(2) || 0))}</td>
                  <td>${numberWithCommas(Number(trade.expired_contracts_premiums?.toFixed(2) || 0))}</td>
                  <td>{trade.calls_bought_back}</td>
                  <td>${numberWithCommas(Number(trade.pnl_calls_bought_back?.toFixed(2) || 0))}</td>
                  <td>{trade.puts_bought_back}</td>
                  <td>${numberWithCommas(Number(trade.pnl_puts_bought_back?.toFixed(2) || 0))}</td>
                  <td>${numberWithCommas(Number(trade.bought_back_contracts_pnl?.toFixed(2) || 0))}</td>
                  <td>{trade.assigned_closed_count}</td>
                  <td>${numberWithCommas(Number(trade.assigned_closed_realized_pnl?.toFixed(2) || 0))}</td>
                  <td>{trade.assigned_opened_count}</td>
                  <td>${numberWithCommas(Number(trade.assigned_opened_mtm_pnl?.toFixed(2) || 0))}</td>
                  <td>${numberWithCommas(Number(trade.assigned_contracts_pnl?.toFixed(2) || 0))}</td>
                </tr>
              ))}
            {!loading && paginatedTrades.length === 0 && (
              <tr>
                <td colSpan={18} className="text-center py-4">
                  No trade data available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pt-[10px]">
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </div>
    </div>
  );
};

export default TradeAnalysis;

