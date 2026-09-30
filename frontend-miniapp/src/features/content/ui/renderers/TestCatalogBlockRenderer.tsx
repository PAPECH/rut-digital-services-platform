import type {
  BlockRendererProps,
  TestCatalogBlock,
} from "@/entities/content/model/types";
import { TestCatalog } from "@/features/form-tests/ui/TestCatalog";

export function TestCatalogBlockRenderer({
  block,
}: BlockRendererProps<TestCatalogBlock>) {
  return <TestCatalog title={block.title} />;
}
