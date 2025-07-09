"use client";

import { useState, useEffect } from "react";
import useFetch from "@/hooks/useFetch";
import { toast } from "sonner";
import CustomButton from "@/components/theme/customButton";
import SearchBar from "@/admin_components/common/searchBar";
import Pagination from "@/admin_components/common/pagination";
import { PuffLoader } from "react-spinners";
import { jsPDF } from "jspdf";
import "jspdf-autotable";
import { CloudArrowDownIcon } from "@/admin_components/icons";

interface Position {
  symbol: string;
  quantity: number;
  current_value: number;
}

const PortfolioATH = () => {
  const [searchValue, setSearchValue] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsOnPage = 10;

  const [portfolioATHValueInput, setPortfolioATHValueInput] = useState<string>("");
  const [portfolioATHDateInput, setPortfolioATHDateInput] = useState<string>("");
  const [accountIdInput, setAccountIdInput] = useState<string>("");
  const [currentNAVInput, setCurrentNAVInput] = useState<string>("");

  const [getPortfolioPositions, { response, loading, error }] = useFetch(
    "/admin/dashboard/",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    }
  );

  const [sendATHInfo, { response: athResponse, loading: athLoading, error: athError }] =
    useFetch("/admin/dashboard/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });

  const fetchDashboardData = () => {
    getPortfolioPositions({ body: JSON.stringify({}) });
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    if (error) {
      toast.error(error?.message);
    }
    if (athError) {
      toast.error(athError?.message);
    }
  }, [error, athError]);

  const handleSubmitATHInfo = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!portfolioATHValueInput || !portfolioATHDateInput || !accountIdInput || !currentNAVInput) {
      toast.error("Please fill out all fields.");
      return;
    }
    sendATHInfo({
      body: JSON.stringify({
        portfolioATHValue: Number(portfolioATHValueInput),
        portfolioATHDate: portfolioATHDateInput,
        accountId: accountIdInput,
        currentNAV: Number(currentNAVInput),
      }),
    })
      .then(() => {
        toast.success("ATH info submitted successfully.");
        fetchDashboardData();
      })
      .catch(() => {
        toast.error("Error submitting ATH info.");
      });
  };

  const handleDownloadPDF = () => {
    const input = document.getElementById("portfolioATHAnalysisTable");
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
    pdf.text("Portfolio All-Time High Analysis Report", pageWidth / 2, 120, { align: "center" });
    const currentDate = new Date().toLocaleDateString();
    pdf.setFontSize(14);
    pdf.text(`Generated on: ${currentDate}`, pageWidth / 2, 140, { align: "center" });

    pdf.addPage();

    const rows = Array.from(input.getElementsByTagName("tr"));
    if (rows.length === 0) return;
    const headers = rows[0].getElementsByTagName("th");
    const headersArray = Array.from(headers).map(header => header.innerText.trim());
    const data = rows.slice(1).map(row =>
      Array.from(row.getElementsByTagName("td")).map(cell => cell.innerText.trim())
    );

    let startY = 20;
    pdf.setFontSize(10);
    pdf.text("Portfolio ATH Analysis", pageWidth / 2, startY, { align: "center" });

    pdf.autoTable({
      head: [headersArray],
      body: data,
      startY: startY + 10,
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

    pdf.save("portfolio_ath_analysis.pdf");
  };

  const positions: Position[] = response?.data?.positions || [];
  const currentCash = response?.data?.cash || 0;
  const currentPortfolioValue = response?.data?.portfolio_value || 0;

  const filteredPositions = positions
    .filter((pos: Position) =>
      searchValue ? pos.symbol.toLowerCase().includes(searchValue.toLowerCase()) : true
    )
    .slice((currentPage - 1) * itemsOnPage, currentPage * itemsOnPage);

  const totalRecords = positions.length;
  const totalPages = Math.ceil(totalRecords / itemsOnPage);

  const handlePageChange = (pageNumber: number) => {
    setCurrentPage(pageNumber);
  };

  const renderPortfolioAllTimeHighAnalysis = () => {
    const athRecords = response?.data?.ath_submissions || [];
    const calculatedData = response?.data?.portfolio_ath || {};
    if (athRecords.length === 0) {
      return <p className="text-center py-4">No Portfolio All Time High records available.</p>;
    }

    const sortedAthRecords = [...athRecords].sort((a, b) => Number(a.account_id) - Number(b.account_id));

    return (
      <div className="mt-8 p-4 rounded-md">
        <h2 className="text-xl font-bold mb-4">Portfolio All Time High Analysis</h2>
        <div className="theme-table">
          <table id="portfolioATHAnalysisTable" className="w-full">
            <thead className="sticky top-0 z-20">
              <tr>
                <th scope="col" className="text-left">Account ID</th>
                <th scope="col" className="text-left">Current NAV</th>
                <th scope="col" className="text-left">Portfolio ATH Value</th>
                <th scope="col" className="text-left">Portfolio ATH Date</th>
                <th scope="col" className="text-left">Calculated New ATH Value</th>
                <th scope="col" className="text-left">ATH Difference</th>
                <th scope="col" className="text-left">Total Options Value</th>
              </tr>
            </thead>
            <tbody>
              {sortedAthRecords.map((record: any, index: number) => {
                const calculated = calculatedData[record.account_id] || {};
                return (
                  <tr key={index}>
                    <td>{record.account_id}</td>
                    <td>${Number(record.currentNAVValue).toFixed(2)}</td>
                    <td>${Number(record.portfolioATHValue).toFixed(2)}</td>
                    <td>{record.portfolioATHDate}</td>
                    <td>
                      {calculated.new_ath_value !== undefined
                        ? "$" + Number(calculated.new_ath_value).toFixed(2)
                        : "-"}
                    </td>
                    <td>
                      {calculated.ath_difference !== undefined
                        ? "$" + Number(calculated.ath_difference).toFixed(2)
                        : "-"}
                    </td>
                    <td>
                      {calculated.total_options_value !== undefined
                        ? "$" + Number(calculated.total_options_value).toFixed(2)
                        : "-"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="ring-1 ring-borderColor bg-white p-4 md:p-7 rounded-[10px] min-h-[50vh]">
      <div className="mb-8 flex flex-col md:flex-row gap-4">
        <div className="flex-1 p-4 border border-gray-300 rounded-md">
          <h2 className="text-lg font-bold mb-4">Submit Portfolio All-Time-High Information</h2>
          <form onSubmit={handleSubmitATHInfo} className="flex flex-col md:flex-row gap-4 items-center">
            <div className="flex flex-col">
              <label htmlFor="athValue" className="text-xs font-medium text-gray-700">
                Portfolio ATH Value:
              </label>
              <input
                type="number"
                id="athValue"
                value={portfolioATHValueInput}
                onChange={(e) => setPortfolioATHValueInput(e.target.value)}
                placeholder="Enter ATH Value"
                className="p-1 border border-gray-400 rounded-md"
              />
            </div>
            <div className="flex flex-col">
              <label htmlFor="athDate" className="text-xs font-medium text-gray-700">
                ATH Date:
              </label>
              <input
                type="date"
                id="athDate"
                value={portfolioATHDateInput}
                onChange={(e) => setPortfolioATHDateInput(e.target.value)}
                className="p-1 border border-gray-400 rounded-md"
              />
            </div>
            <div className="flex flex-col">
              <label htmlFor="currentNAV" className="text-xs font-medium text-gray-700">
                Current NAV:
              </label>
              <input
                type="number"
                id="currentNAV"
                value={currentNAVInput}
                onChange={(e) => setCurrentNAVInput(e.target.value)}
                placeholder="Enter Current NAV"
                className="p-1 border border-gray-400 rounded-md"
              />
            </div>
            <div className="flex flex-col">
              <label htmlFor="accountId" className="text-xs font-medium text-gray-700">
                Account ID:
              </label>
              <input
                type="text"
                id="accountId"
                value={accountIdInput}
                onChange={(e) => setAccountIdInput(e.target.value)}
                placeholder="Enter Account ID"
                className="p-1 border border-gray-400 rounded-md"
              />
            </div>
            <CustomButton variantType="filled" type="submit">
              Submit
            </CustomButton>
          </form>
        </div>
        <div className="flex items-center">
          <CustomButton
            variantType="filled"
            type="button"
            rightIcon={<CloudArrowDownIcon />}
            onClick={handleDownloadPDF}
          >
            Download as PDF
          </CustomButton>
        </div>
      </div>

      {renderPortfolioAllTimeHighAnalysis()}

    </div>
  );
};

export default PortfolioATH;
