import Diagnostics from "@/components/diagnostics";
export default async function Page({searchParams}:{searchParams:Promise<{trace?:string}>}){
 const {trace}=await searchParams;return <Diagnostics key={trace||""} initialId={trace||""}/>;
}
