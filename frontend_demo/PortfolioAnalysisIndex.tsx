"use client";

import { useState, useEffect } from "react";
import useFetch from "@/hooks/useFetch";
import { toast } from "sonner";
import CustomButton from "@/components/theme/customButton";
import SearchBar from "@/admin_components/common/searchBar";
import Pagination from "@/admin_components/common/pagination";
import { PuffLoader } from "react-spinners";
import { AiOutlineArrowUp, AiOutlineArrowDown } from "react-icons/ai";
import { CloudArrowDownIcon } from "@/admin_components/icons";
import { jsPDF } from "jspdf";
import "jspdf-autotable";

const numberWithCommas = (value: number | string) => {
  if (value === undefined || value === null) return "0";
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
};

const Portfolios = () => {
  const [percentageUp, setPercentageUp] = useState(5);
  const [percentageDown, setPercentageDown] = useState(5);
  const [expirationThreshold, setExpirationThreshold] = useState(5);
  const [searchValue, setSearchValue] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsOnPage = 10;

  const [getPortfolioExposures, { response, loading, error }] = useFetch(
    "/admin/dashboard/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    }
  );

  useEffect(() => {
    getPortfolioExposures({
      body: JSON.stringify({
        percentageUp,
        percentageDown,
        expirationThreshold,
      }),
    });
  }, []);

  useEffect(() => {
    if (error) {
      toast.error(error?.message);
    }
  }, [error]);

  const generateNewValues = () => {
    getPortfolioExposures({
      body: JSON.stringify({
        percentageUp,
        percentageDown,
        expirationThreshold,
      }),
    });
  };

  const handleInputChange = (setter: any) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setter(value ? Number(value) : undefined);
  };

  const portfolios = response?.data?.portfolio_exposures || [];
  const sortedPortfolios = [...portfolios].sort(
    (a, b) => Number(a.account_id) - Number(b.account_id)
  );

  const totalRecords = sortedPortfolios.length;
  const totalPages = Math.ceil(totalRecords / itemsOnPage);

  const filteredPortfolios = sortedPortfolios
    .filter((portfolio: any) =>
      searchValue ? portfolio.account_id?.toString().includes(searchValue) : true
    )
    .slice((currentPage - 1) * itemsOnPage, currentPage * itemsOnPage);

  const handlePageChange = (pageNumber: number) => {
    setCurrentPage(pageNumber);
  };

  const handleDownloadPDF = () => {
    const input = document.getElementById("portfolioTable");
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
    pdf.text("Portfolio Analysis Report", pageWidth / 2, 120, { align: "center" });
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

    const firstTableColumns = [0, 1, 2, 3, 4];
    const secondTableColumns = [5, 6, 7, 8, 9, 10, 11, 12];

    const extractColumns = (columns: number[]) => {
      const newHeaders = columns.map(index => headersArray[index]);
      const newData = data.map(row => columns.map(index => row[index]));
      return { newHeaders, newData };
    };

    const { newHeaders: firstHeaders, newData: firstData } = extractColumns(firstTableColumns);
    const { newHeaders: secondHeaders, newData: secondData } = extractColumns(secondTableColumns);

    secondHeaders[3] = `ITM Contracts (under ${expirationThreshold}d)`;
    secondHeaders[4] = `Exposure (under ${expirationThreshold}d)`;
    secondHeaders[5] = `ITM Contracts (over ${expirationThreshold}d)`;
    secondHeaders[6] = `Exposure (over ${expirationThreshold}d)`;

    let startY = 20;
    pdf.setFontSize(10);
    pdf.text("General Portfolio Metrics", pageWidth / 2, startY, { align: "center" });

    pdf.autoTable({
      head: [firstHeaders],
      body: firstData,
      startY: startY + 10,
      theme: "grid",
      styles: { fontSize: 10, cellPadding: 3, font: "times" },
      headStyles: { fillColor: [0, 0, 0], textColor: [255, 255, 255], fontStyle: "bold" },
      bodyStyles: { textColor: [0, 0, 0], font: "times" },
      alternateRowStyles: { fillColor: [230, 230, 255] },
    });

    const tableHeight = pdf.lastAutoTable.finalY + 10;
    pdf.setFontSize(10);
    pdf.text("Exposure & Additional Metrics", pageWidth / 2, tableHeight, { align: "center" });

    pdf.autoTable({
      head: [secondHeaders],
      body: secondData,
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

    pdf.save("portfolio_analysis.pdf");
  };

  return (
    <div className="ring-1 ring-borderColor bg-white p-4 md:p-7 rounded-[10px] min-h-[50vh]">
      <div className="flex flex-col md:flex-row justify-between items-center mb-8 gap-5">
        <div className="basis-[100%] md:basis-[33.33%]">
          <SearchBar
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            placeholder="Search by Account ID"
          />
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            generateNewValues();
          }}
          className="flex flex-col md:flex-row items-center gap-2"
        >
          <div className="flex items-center gap-1 border border-black rounded-md p-1">
            <AiOutlineArrowUp className="text-green-500 text-lg" />
            <label htmlFor="percentageUp" className="text-xs font-medium text-gray-700">
              Portfolio Upward Exposure (%):
            </label>
            <input
              type="number"
              id="percentageUp"
              name="percentageUp"
              value={percentageUp}
              onChange={(e) => setPercentageUp(Number(e.target.value))}
              className="p-1 w-12 shadow-sm sm:text-xs border border-black rounded-md"
            />
          </div>

          <div className="flex items-center gap-1 border border-black rounded-md p-1">
            <AiOutlineArrowDown className="text-red-500 text-lg" />
            <label htmlFor="percentageDown" className="text-xs font-medium text-gray-700">
              Portfolio Downward Exposure (%):
            </label>
            <input
              type="number"
              id="percentageDown"
              name="percentageDown"
              value={percentageDown}
              onChange={(e) => setPercentageDown(Number(e.target.value))}
              className="p-1 w-12 shadow-sm sm:text-xs border border-black rounded-md"
            />
          </div>

          <div className="flex items-center gap-1 border border-black rounded-md p-1">
            <label htmlFor="expirationThreshold" className="text-xs font-medium text-gray-700">
              Contract Expiration Threshold (days):
            </label>
            <input
              type="number"
              id="expirationThreshold"
              name="expirationThreshold"
              value={expirationThreshold}
              onChange={(e) => setExpirationThreshold(Number(e.target.value))}
              className="p-1 w-20 shadow-sm sm:text-xs border border-black rounded-md"
            />
          </div>

          <CustomButton variantType="filled" className="mt-2" onClick={generateNewValues}>
            Submit
          </CustomButton>
        </form>

        <div>
          <CustomButton variantType="filled" rightIcon={<CloudArrowDownIcon />} onClick={handleDownloadPDF}>
            Download as PDF
          </CustomButton>
        </div>
      </div>

      <div className="theme-table">
        <table id="portfolioTable">
          <thead className="sticky top-0 z-20">
            <tr>
              <th scope="col">Account ID</th>
              <th scope="col">Current Equity Value</th>
              <th scope="col">Current Exposure Value</th>
              <th scope="col">Current Leverage</th>
              <th scope="col">Total Exposure Value With Options</th>
              <th scope="col">Exposure Value Given {percentageDown}% Decrease</th>
              <th scope="col">Equity Value Given {percentageDown}% Decrease</th>
              <th scope="col">Leverage Given {percentageDown}% Decrease</th>
              <th scope="col">ITM Contracts (under {expirationThreshold}d Expiry)</th>
              <th scope="col">Exposure (under {expirationThreshold}d Expiry)</th>
              <th scope="col">ITM Contracts (over {expirationThreshold}d Expiry)</th>
              <th scope="col">Exposure (over {expirationThreshold}d Expiry)</th>
              <th scope="col">Exposure Value Given {percentageUp}% Increase</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={13}>
                  <div className="w-full min-h-[300px] flex items-center justify-center">
                    <PuffLoader color="#ff782c" />
                  </div>
                </td>
              </tr>
            )}
            {!loading &&
              filteredPortfolios.map((portfolio: any) => (
                <tr key={portfolio.account_id}>
                  <td>{portfolio.account_id}</td>
                  <td>${numberWithCommas(portfolio.current_account_value)}</td>
                  <td>${numberWithCommas(portfolio.total_equity_value)}</td>
                  <td>{portfolio.current_leverage?.toFixed(3)}x</td>
                  <td>${numberWithCommas(portfolio.total_exposure_value)}</td>
                  <td>${numberWithCommas(portfolio.what_if_down_exposure?.toFixed(3))}</td>
                  <td>${numberWithCommas(portfolio.what_if_down_equity?.toFixed(3))}</td>
                  <td>{portfolio.what_if_down_leverage?.toFixed(3)}x</td>
                  <td>{portfolio.short_term_puts_itm}</td>
                  <td>${numberWithCommas(portfolio.short_term_puts_exposure?.toFixed(3))}</td>
                  <td>{portfolio.long_term_puts_itm}</td>
                  <td>${numberWithCommas(portfolio.long_term_puts_exposure?.toFixed(3))}</td>
                  <td>${numberWithCommas(portfolio.what_if_up_exposure?.toFixed(3))}</td>
                </tr>
              ))}
            {!loading && filteredPortfolios.length === 0 && (
              <tr>
                <td colSpan={13} className="text-center py-4">
                  No portfolio data available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="pt-[10px]">
        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={handlePageChange} />
      </div>
    </div>
  );
};

export default Portfolios;
